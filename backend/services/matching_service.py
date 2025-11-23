"""
匹配服务 - 整合向量搜索和 LLM 评分
"""
import logging
from typing import List, Dict
from database.database import get_db_connection
from services.vector_service import get_vector_service
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

async def match_papers(user_requirement: str, top_k: int = 50) -> List[Dict]:
    """
    匹配论文的完整流程：
    1. 将用户需求转换为查询向量
    2. 在向量数据库中搜索 Top-K 相似论文
    3. 使用 LLM 对每篇论文进行评分
    4. 按分数排序返回
    
    返回: [{"paper_id": str, "title": str, "abstract": str, "score": float, "reason": str, ...}, ...]
    """
    try:
        # 1. 向量搜索
        logger.info(f"开始向量搜索，需求: {user_requirement[:50]}...")
        vector_service = get_vector_service()
        similar_papers = vector_service.search_similar(user_requirement, top_k=top_k)
        
        if not similar_papers:
            logger.warning("未找到相似论文")
            return []
        
        # 2. 从数据库获取论文详细信息
        conn = get_db_connection()
        cursor = conn.cursor()
        
        paper_details = []
        for paper_id, similarity_score in similar_papers:
            # 尝试通过 arxiv_id 查找
            cursor.execute("SELECT * FROM papers WHERE arxiv_id = ?", (paper_id,))
            row = cursor.fetchone()
            
            if row:
                paper_details.append({
                    "paper_id": paper_id,
                    "title": row["title"],
                    "abstract": row["abstract"],
                    "authors": row["authors"],
                    "published_date": row["published_date"],
                    "categories": row["categories"],
                    "pdf_url": row["pdf_url"],
                    "similarity_score": similarity_score
                })
            else:
                # 如果找不到，使用向量数据库中的元数据
                logger.warning(f"论文 {paper_id} 在数据库中不存在，使用向量数据库元数据")
                # 这里可以从 ChromaDB 获取元数据，但为了简化，我们跳过
                continue
        
        conn.close()
        
        if not paper_details:
            logger.warning("未找到论文详细信息")
            return []
        
        # 3. LLM 评分
        logger.info(f"开始 LLM 评分，共 {len(paper_details)} 篇论文")
        llm_service = get_llm_service()
        
        llm_results = await llm_service.score_papers_batch(
            user_requirement,
            paper_details
        )
        
        # 4. 合并结果并排序
        # 创建评分字典以便快速查找
        score_dict = {r["paper_id"]: r for r in llm_results}
        
        final_results = []
        for paper in paper_details:
            paper_id = paper["paper_id"]
            if paper_id in score_dict:
                final_results.append({
                    **paper,
                    "score": score_dict[paper_id]["score"],
                    "reason": score_dict[paper_id]["reason"]
                })
        
        # 按 LLM 评分排序（已经排序，但确保）
        final_results.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"匹配完成，返回 {len(final_results)} 篇论文")
        
        return final_results
        
    except Exception as e:
        logger.error(f"匹配论文失败: {str(e)}")
        raise

