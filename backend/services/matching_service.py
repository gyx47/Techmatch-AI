"""
匹配服务 - 整合 Query Expansion + Vector Search + LLM Re-ranking
"""
import asyncio
import logging
import json
import time
from typing import List, Dict, Tuple
from database.database import get_db_connection
from services.vector_service import get_vector_service
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

async def match_papers(user_requirement: str, top_k: int = 50) -> List[Dict]:
    try:
        start_time = time.time()
        llm_service = get_llm_service()
        vector_service = get_vector_service()

        # ---------------------------------------------------------
        # 步骤 1: 查询扩展 (Query Expansion) - 提升召回率的关键！
        # ---------------------------------------------------------
        logger.info(f"原始需求: {user_requirement}")
        # 让 LLM 把 "我要做工业质检" 变成 "defect detection, surface anomaly detection, YOLO, CNN..."
        expanded_query = await llm_service.expand_query(user_requirement)
        
        # ---------------------------------------------------------
        # 步骤 2: 向量搜索 (Coarse Ranking)
        # ---------------------------------------------------------
        # 使用扩展后的 query 去搜索，但保留原始 query 用于后续 LLM 评分
        logger.info(f"使用增强Query进行向量搜索...")
        coarse_start_time = time.time()
        similar_papers = vector_service.search_similar(expanded_query, top_k=top_k)
        coarse_elapsed = time.time() - coarse_start_time
        
        if not similar_papers:
            return []
        
        logger.info(f"向量搜索（粗排）耗时: {coarse_elapsed:.2f} 秒")

        # ---------------------------------------------------------
        # 步骤 3: 数据填充 (Hydration) - 使用线程池执行，避免阻塞事件循环
        # ---------------------------------------------------------
        # 过滤掉成果ID（achievement_* 前缀），只处理论文
        paper_ids = [p[0] for p in similar_papers if not p[0].startswith("achievement_")]
        
        if not paper_ids:
            return []
        
        # 将同步的数据库查询放到线程池中执行
        def fetch_papers_from_db(paper_ids: List[str]):
            """从数据库批量获取论文详细信息（同步函数，在线程池中执行）"""
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 优化 SQL：一次性查出所有数据，不再循环查
            placeholders = ','.join(['?'] * len(paper_ids))
            query = f"SELECT * FROM papers WHERE arxiv_id IN ({placeholders})"
            cursor.execute(query, paper_ids)
            rows = cursor.fetchall()
            conn.close()
            return rows
        
        rows = await asyncio.to_thread(fetch_papers_from_db, paper_ids)

        # 构建详细列表，保持向量搜索的顺序（因为 SQL 返回顺序是不定的）
        # 只处理论文ID，过滤掉成果ID
        row_dict = {row["arxiv_id"]: row for row in rows}
        paper_details = []
        
        for pid, vec_score in similar_papers:
            # 跳过成果ID
            if pid.startswith("achievement_"):
                continue
            if pid in row_dict:
                row = row_dict[pid]
                paper_details.append({
                    "paper_id": pid,
                    "title": row["title"],
                    "abstract": row["abstract"],
                    "authors": row["authors"],
                    "published_date": row["published_date"],
                    "categories": row["categories"],
                    "pdf_url": row["pdf_url"],
                    "vector_score": vec_score # 保留向量分作为参考
                })
        # ---------------------------------------------------------
        # 步骤 4: 防御性排序
        # ---------------------------------------------------------
        # 虽然 similar_papers 通常是有序的，但为了防止上游（VectorService）乱序，
        # 或者 row_dict 处理过程中出现的意外，
        # 这里显式地按 vector_score 从大到小再排一次，确保万无一失。
        paper_details.sort(key=lambda x: x["vector_score"], reverse=True)
        # ---------------------------------------------------------
        # 步骤 5: LLM 精排 (Re-ranking)
        # ---------------------------------------------------------
        logger.info(f"开始 LLM 精排，候选数量: {len(paper_details)}")
        
        # 注意：评分时要用"原始需求"，因为那是用户真正的意图
        rerank_start_time = time.time()
        ranked_results = await llm_service.score_papers_batch(
            user_requirement, 
            paper_details
        )
        rerank_elapsed = time.time() - rerank_start_time
        logger.info(f"LLM 精排耗时: {rerank_elapsed:.2f} 秒")
        
        # 合并详细信息
        final_output = []
        detail_map = {p["paper_id"]: p for p in paper_details}
        
        for res in ranked_results:
            pid = res["paper_id"]
            if pid in detail_map:
                paper = detail_map[pid]
                final_output.append({
                    **paper,
                    "score": res["score"],   # LLM 给的 0-100 分
                    "reason": res["reason"], # 犀利点评
                    "match_type": get_match_label(res["score"]) # 加上标签
                })

        total_elapsed = time.time() - start_time
        logger.info(f"论文匹配总耗时: {total_elapsed:.2f} 秒（粗排: {coarse_elapsed:.2f}秒, 精排: {rerank_elapsed:.2f}秒）")

        return final_output

    except Exception as e:
        logger.error(f"匹配流程异常: {str(e)}")
        raise

def get_match_label(score):
    if score >= 90: return "S级-完美适配"
    if score >= 75: return "A级-技术相关"
    if score >= 60: return "B级-潜在可用"
    return "C级-参考"

def _classify_ids(vector_ids: List[str]) -> Tuple[List[str], List[int]]:
    """根据ID前缀分类：返回 (paper_ids, achievement_ids)"""
    paper_ids = []
    achievement_ids = []
    
    for vid in vector_ids:
        if vid.startswith("achievement_"):
            try:
                achievement_id = int(vid.replace("achievement_", ""))
                achievement_ids.append(achievement_id)
            except ValueError:
                logger.warning(f"无法解析成果ID: {vid}")
        else:
            paper_ids.append(vid)
    
    return paper_ids, achievement_ids

def _normalize_for_llm(items: List[Dict]) -> List[Dict]:
    """统一格式，让 LLM 能理解论文和成果"""
    normalized = []
    for item in items:
        if item.get("item_type") == "paper":
            normalized.append({
                "paper_id": item["paper_id"],
                "title": item["title"],
                "abstract": item["abstract"],
                "item_type": "paper"
            })
        else:  # achievement
            # 将成果转换为类似论文的格式供 LLM 评分
            abstract = item.get("description", "")
            if item.get("application"):
                abstract += f"\n应用场景: {item['application']}"
            normalized.append({
                "paper_id": f"achievement_{item['achievement_id']}",  # LLM 需要 paper_id 字段
                "title": item.get("name", ""),
                "abstract": abstract,
                "item_type": "achievement"
            })
    return normalized

async def match_all(user_requirement: str, top_k: int = 50) -> List[Dict]:
    """
    统一匹配论文和成果
    返回混合结果，包含 item_type 标记
    """
    try:
        start_time = time.time()
        llm_service = get_llm_service()
        vector_service = get_vector_service()

        # ---------------------------------------------------------
        # 步骤 1: 查询扩展 (Query Expansion)
        # ---------------------------------------------------------
        logger.info(f"原始需求: {user_requirement}")
        expanded_query = await llm_service.expand_query(user_requirement)
        
        # ---------------------------------------------------------
        # 步骤 2: 向量搜索 (Coarse Ranking) - 返回论文和成果的混合结果
        # ---------------------------------------------------------
        logger.info(f"使用增强Query进行向量搜索（包含论文和成果）...")
        coarse_start_time = time.time()
        similar_items = vector_service.search_similar(expanded_query, top_k=top_k)
        coarse_elapsed = time.time() - coarse_start_time
        
        if not similar_items:
            return []

        # ---------------------------------------------------------
        # 步骤 3: 根据ID前缀分类
        # ---------------------------------------------------------
        vector_ids = [item[0] for item in similar_items]
        paper_ids, achievement_ids = _classify_ids(vector_ids)
        
        logger.info(f"找到 {len(paper_ids)} 篇论文，{len(achievement_ids)} 个成果")
        logger.info(f"向量搜索（粗排）耗时: {coarse_elapsed:.2f} 秒")

        # ---------------------------------------------------------
        # 步骤 4: 数据填充 (Hydration) - 分别查询两个表
        # ---------------------------------------------------------
        def fetch_data_from_db(paper_ids: List[str], achievement_ids: List[int]):
            """从数据库批量获取论文和成果详细信息（同步函数，在线程池中执行）"""
            conn = get_db_connection()
            cursor = conn.cursor()
            
            papers = []
            achievements = []
            
            # 查询论文
            if paper_ids:
                placeholders = ','.join(['?'] * len(paper_ids))
                query = f"SELECT * FROM papers WHERE arxiv_id IN ({placeholders})"
                cursor.execute(query, paper_ids)
                papers = cursor.fetchall()
            
            # 查询成果
            if achievement_ids:
                placeholders = ','.join(['?'] * len(achievement_ids))
                query = f"SELECT * FROM published_achievements WHERE id IN ({placeholders}) AND status = 'published'"
                cursor.execute(query, achievement_ids)
                achievements = cursor.fetchall()
            
            conn.close()
            return papers, achievements
        
        papers_rows, achievements_rows = await asyncio.to_thread(
            fetch_data_from_db, paper_ids, achievement_ids
        )

        # ---------------------------------------------------------
        # 步骤 5: 构建统一格式的详细列表
        # ---------------------------------------------------------
        # 构建映射表（转换为字典，方便使用 .get() 方法）
        paper_dict = {row["arxiv_id"]: dict(row) for row in papers_rows}
        achievement_dict = {row["id"]: dict(row) for row in achievements_rows}
        
        all_details = []
        
        # 处理向量搜索结果，保持顺序
        for vid, vec_score in similar_items:
            if vid.startswith("achievement_"):
                # 处理成果
                try:
                    achievement_id = int(vid.replace("achievement_", ""))
                    if achievement_id in achievement_dict:
                        row = achievement_dict[achievement_id]
                        # 解析 JSON 字段
                        cooperation_mode = []
                        if row.get('cooperation_mode'):
                            try:
                                cooperation_mode = json.loads(row['cooperation_mode'])
                            except:
                                pass
                        
                        all_details.append({
                            "item_type": "achievement",
                            "achievement_id": achievement_id,
                            "name": row.get("name", ""),
                            "description": row.get("description", ""),
                            "application": row.get("application"),
                            "field": row.get("field"),
                            "cooperation_mode": cooperation_mode,
                            "contact_name": row.get("contact_name"),
                            "contact_phone": row.get("contact_phone"),
                            "contact_email": row.get("contact_email"),
                            "pdf_url": None,  # 成果没有 PDF
                            "vector_score": vec_score
                        })
                except ValueError:
                    logger.warning(f"无法解析成果ID: {vid}")
            else:
                # 处理论文
                if vid in paper_dict:
                    row = paper_dict[vid]
                    all_details.append({
                        "item_type": "paper",
                        "paper_id": vid,
                        "title": row.get("title", ""),
                        "abstract": row.get("abstract", ""),
                        "authors": row.get("authors", ""),
                        "published_date": row.get("published_date"),
                        "categories": row.get("categories"),
                        "pdf_url": row.get("pdf_url"),
                        "vector_score": vec_score
                    })
        
        # ---------------------------------------------------------
        # 步骤 6: 防御性排序
        # ---------------------------------------------------------
        all_details.sort(key=lambda x: x["vector_score"], reverse=True)
        
        # ---------------------------------------------------------
        # 步骤 7: LLM 精排 (Re-ranking) - 一起评分
        # ---------------------------------------------------------
        logger.info(f"开始 LLM 精排，候选数量: {len(all_details)}（论文+成果）")
        
        # 统一格式供 LLM 评分
        normalized_items = _normalize_for_llm(all_details)
        
        # 调用 LLM 评分（使用原始需求）
        rerank_start_time = time.time()
        ranked_results = await llm_service.score_papers_batch(
            user_requirement,
            normalized_items
        )
        rerank_elapsed = time.time() - rerank_start_time
        logger.info(f"LLM 精排耗时: {rerank_elapsed:.2f} 秒")
        
        # ---------------------------------------------------------
        # 步骤 8: 合并结果
        # ---------------------------------------------------------
        final_output = []
        detail_map = {}
        
        # 为论文和成果分别建立映射
        for detail in all_details:
            if detail["item_type"] == "paper":
                detail_map[detail["paper_id"]] = detail
            else:
                detail_map[f"achievement_{detail['achievement_id']}"] = detail
        
        for res in ranked_results:
            pid = res["paper_id"]  # LLM 返回的 paper_id（成果也是这个字段名）
            if pid in detail_map:
                item = detail_map[pid]
                final_output.append({
                    **item,
                    "score": res["score"],   # LLM 给的 0-100 分
                    "reason": res["reason"], # 犀利点评
                    "match_type": get_match_label(res["score"]) # 加上标签
                })

        total_elapsed = time.time() - start_time
        logger.info(f"统一匹配总耗时: {total_elapsed:.2f} 秒（粗排: {coarse_elapsed:.2f}秒, 精排: {rerank_elapsed:.2f}秒）")

        return final_output

    except Exception as e:
        logger.error(f"统一匹配流程异常: {str(e)}")
        raise