"""
需求匹配服务 - 科研成果找需求（优化版）
"""
import logging
import time
from typing import List, Dict
from database.database import get_db_connection
from services.vector_service import get_vector_service
from services.llm_service import get_llm_service
from services.matching_service import validate_user_input

logger = logging.getLogger(__name__)

async def match_requirements_for_paper(
    paper_title: str, 
    paper_abstract: str,
    paper_categories: str = "",
    top_k: int = 20
) -> List[Dict]:
    """
    为科研成果匹配需求（优化版：使用查询扩展，与需求匹配流程一致）
    """
    try:
        start_time = time.time()
        llm_service = get_llm_service()
        vector_service = get_vector_service()
        
        # 合并用户输入的成果文字
        achievement_text = f"{paper_title}\n{paper_abstract}".strip()
        
        # ---------------------------------------------------------
        # 步骤 0: 输入质量检测（快速规则检测）
        # ---------------------------------------------------------
        is_valid, reason = validate_user_input(achievement_text)
        if not is_valid:
            logger.warning(f"输入质量检测失败: {reason}, 输入: {achievement_text[:50]}...")
            return []  # 直接返回空结果，不进行查询扩展和向量搜索
        
        # ---------------------------------------------------------
        # 步骤 1: 查询扩展 (Query Expansion) - 与需求匹配一致
        # ---------------------------------------------------------
        # 如果paper_title是默认值"论文"，只显示paper_abstract用于日志
        if paper_title and paper_title.strip() and paper_title != "论文":
            logger.info(f"原始成果: {achievement_text[:200]}...")
        else:
            logger.info(f"原始成果: {paper_abstract[:200]}...")
        expanded_query = await llm_service.expand_query(achievement_text)
        
        # 检查LLM是否判断输入无意义
        if expanded_query and expanded_query.strip().upper() == "[INVALID_INPUT]":
            logger.warning(f"LLM判断输入无意义: {achievement_text[:50]}...")
            return []  # 直接返回空结果
        
        # ---------------------------------------------------------
        # 步骤 2: 向量搜索 (Coarse Ranking)
        # ---------------------------------------------------------
        logger.info(f"使用增强Query进行向量搜索...")
        coarse_start_time = time.time()
        similar_requirements = vector_service.search_requirements(expanded_query, top_k=top_k)
        coarse_elapsed = time.time() - coarse_start_time
        
        logger.info(f"向量搜索（粗排）耗时: {coarse_elapsed:.2f} 秒")
        logger.info(f"向量搜索返回: {len(similar_requirements)} 个需求")
        
        if not similar_requirements:
            return []
        
        # ---------------------------------------------------------
        # 步骤 3: 数据填充 (Hydration) - 获取需求详情
        # ---------------------------------------------------------
        requirement_ids = [r[0] for r in similar_requirements]
        
        # 区分系统需求和发布需求
        system_requirement_ids = [rid for rid in requirement_ids if not rid.startswith("published_need_")]
        published_need_ids = []
        for rid in requirement_ids:
            if rid.startswith("published_need_"):
                try:
                    need_id = int(rid.replace("published_need_", ""))
                    published_need_ids.append(need_id)
                except ValueError:
                    logger.warning(f"无法解析发布需求ID: {rid}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        rows = []
        
        # 查询系统需求
        if system_requirement_ids:
            placeholders = ','.join(['?'] * len(system_requirement_ids))
            query = f"""
                SELECT * FROM requirements 
                WHERE requirement_id IN ({placeholders}) 
                AND status = 'active'
            """
            cursor.execute(query, system_requirement_ids)
            system_rows = cursor.fetchall()
            # 转换为字典列表
            rows.extend([dict(row) for row in system_rows])
            logger.info(f"系统需求查询返回: {len(system_rows)} 条记录")
        
        # 查询发布需求
        published_rows = []
        if published_need_ids:
            placeholders = ','.join(['?'] * len(published_need_ids))
            query = f"""
                SELECT * FROM published_needs 
                WHERE id IN ({placeholders}) 
                AND status = 'published'
            """
            cursor.execute(query, published_need_ids)
            published_rows_raw = cursor.fetchall()
            # 转换发布需求的字段格式，补充缺失字段
            for row in published_rows_raw:
                row_dict = dict(row)
                # 转换为统一格式，补充系统需求表中的字段（发布需求没有这些字段）
                published_rows.append({
                    "requirement_id": f"published_need_{row_dict['id']}",  # 使用向量ID格式
                    "title": row_dict.get("title", ""),
                    "description": row_dict.get("description", ""),
                    "industry": row_dict.get("industry", ""),
                    "pain_points": "",  # 发布需求没有此字段
                    "technical_level": "",  # 发布需求没有此字段
                    "market_size": "",  # 发布需求没有此字段
                })
            logger.info(f"发布需求查询返回: {len(published_rows)} 条记录")
        
        conn.close()
        
        # 合并结果
        all_rows = rows + published_rows
        logger.info(f"数据库查询返回总计: {len(all_rows)} 条记录")
        
        if not all_rows:
            logger.warning("数据库未找到对应的需求记录")
            return []
        
        # 构建详细列表，保持顺序
        row_dict = {row["requirement_id"]: row for row in all_rows}
        requirement_details = []
        
        for rid, vec_score in similar_requirements:
            if rid in row_dict:
                row = row_dict[rid]
                requirement_details.append({
                    "requirement_id": rid,
                    "title": row.get("title", ""),
                    "description": row.get("description", ""),
                    "industry": row.get("industry", ""),
                    "pain_points": row.get("pain_points") or "",  # 发布需求为空字符串
                    "technical_level": row.get("technical_level") or "",  # 发布需求为空字符串
                    "market_size": row.get("market_size") or "",  # 发布需求为空字符串
                    "vector_score": vec_score
                })
        
        logger.info(f"成功构建 {len(requirement_details)} 个需求详情")
        
        # ---------------------------------------------------------
        # 步骤 4: LLM评估匹配度 (Re-ranking) - 使用原始输入
        # ---------------------------------------------------------
        if not requirement_details:
            return []
        
        logger.info(f"开始 LLM 精排，候选数量: {len(requirement_details)}")
        
        # 注意：评估时使用原始成果文字，因为那是用户的真实意图
        rerank_start_time = time.time()
        try:
            ranked_results = await llm_service.score_requirements_for_paper(
                achievement_text=achievement_text,  # 使用原始输入
                requirements=requirement_details
            )
            rerank_elapsed = time.time() - rerank_start_time
            logger.info(f"LLM评估（精排）耗时: {rerank_elapsed:.2f} 秒")
        except Exception as e:
            logger.error(f"LLM评估失败: {e}")
            rerank_elapsed = time.time() - rerank_start_time
            # 如果没有LLM结果，使用向量分数排序
            ranked_results = [
                {
                    "requirement_id": req["requirement_id"],
                    "score": int(req["vector_score"] * 100),
                    "reason": f"向量相似度: {req['vector_score']:.4f}",
                    "implementation_suggestion": ""
                }
                for req in requirement_details
            ]
            ranked_results.sort(key=lambda x: x["score"], reverse=True)
        
        # 合并详细信息
        final_output = []
        detail_map = {r["requirement_id"]: r for r in requirement_details}
        
        for res in ranked_results:
            rid = res["requirement_id"]
            if rid in detail_map:
                req = detail_map[rid]
                final_output.append({
                    **req,
                    "score": res["score"],
                    "reason": res["reason"],
                    "match_type": get_requirement_match_label(res["score"]),
                    "implementation_suggestion": res.get("implementation_suggestion", "")
                })
        
        total_elapsed = time.time() - start_time
        logger.info(f"成果匹配总耗时: {total_elapsed:.2f} 秒（粗排: {coarse_elapsed:.2f}秒, 精排: {rerank_elapsed:.2f}秒）")
        
        cleaned_output = []
        for req in final_output:
            cleaned_req = {
                "requirement_id": req.get("requirement_id", ""),
                "title": req.get("title", ""),
                "description": req.get("description", ""),
                "industry": req.get("industry", ""),
                "pain_points": req.get("pain_points", "") or "",  # 确保不是None
                "technical_level": req.get("technical_level", ""),
                "market_size": req.get("market_size", ""),
                "score": req.get("score", 0),
                "reason": req.get("reason", ""),
                "match_type": req.get("match_type", ""),
                "implementation_suggestion": req.get("implementation_suggestion", ""),
                "vector_score": req.get("vector_score", 0.0)
            }
            cleaned_output.append(cleaned_req)

        logger.info(f"数据清洗完成，返回 {len(cleaned_output)} 个结果")
        return cleaned_output
        
    except Exception as e:
        logger.error(f"需求匹配流程异常: {str(e)}", exc_info=True)
        raise

def get_requirement_match_label(score: int) -> str:
    """需求匹配标签"""
    if score >= 90: return "S级-直接落地"
    if score >= 75: return "A级-高价值适配"
    if score >= 60: return "B级-需技术适配"
    if score >= 40: return "C级-理论相关"
    return "D级-关联性弱"