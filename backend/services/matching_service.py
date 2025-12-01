"""
匹配服务 - 整合 Query Expansion + Vector Search + LLM Re-ranking
"""
import logging
from typing import List, Dict
from database.database import get_db_connection
from services.vector_service import get_vector_service
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

async def match_papers(user_requirement: str, top_k: int = 50) -> List[Dict]:
    try:
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
        similar_papers = vector_service.search_similar(expanded_query, top_k=top_k)
        
        if not similar_papers:
            return []

        # ---------------------------------------------------------
        # 步骤 3: 数据填充 (Hydration)
        # ---------------------------------------------------------
        paper_ids = [p[0] for p in similar_papers]
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 优化 SQL：一次性查出所有数据，不再循环查
        placeholders = ','.join(['?'] * len(paper_ids))
        query = f"SELECT * FROM papers WHERE arxiv_id IN ({placeholders})"
        cursor.execute(query, paper_ids)
        rows = cursor.fetchall()
        conn.close()

        # 构建详细列表，保持向量搜索的顺序（因为 SQL 返回顺序是不定的）
        row_dict = {row["arxiv_id"]: row for row in rows}
        paper_details = []
        
        for pid, vec_score in similar_papers:
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
        ranked_results = await llm_service.score_papers_batch(
            user_requirement, 
            paper_details
        )
        
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

        return final_output

    except Exception as e:
        logger.error(f"匹配流程异常: {str(e)}")
        raise

def get_match_label(score):
    if score >= 90: return "S级-完美适配"
    if score >= 75: return "A级-技术相关"
    if score >= 60: return "B级-潜在可用"
    return "C级-参考"