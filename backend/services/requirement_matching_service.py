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
        logger.info(f"原始成果: {achievement_text[:200]}...")
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 一次性获取所有需求详情
        placeholders = ','.join(['?'] * len(requirement_ids))
        query = f"""
            SELECT * FROM requirements 
            WHERE requirement_id IN ({placeholders}) 
            AND status = 'active'
        """
        cursor.execute(query, requirement_ids)
        rows = cursor.fetchall()
        conn.close()
        
        logger.info(f"数据库查询返回: {len(rows)} 条记录")
        
        if not rows:
            logger.warning("数据库未找到对应的需求记录")
            # 检查需求表是否存在数据
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as total FROM requirements WHERE status = 'active'")
                total = cursor.fetchone()["total"]
                conn.close()
                logger.info(f"需求表活跃需求总数: {total}")
            except Exception as e:
                logger.error(f"检查需求表失败: {e}")
            return []
        
        # 构建详细列表，保持顺序
        row_dict = {row["requirement_id"]: row for row in rows}
        requirement_details = []
        
        for rid, vec_score in similar_requirements:
            if rid in row_dict:
                row = row_dict[rid]
                requirement_details.append({
                    "requirement_id": rid,
                    "title": row["title"],
                    "description": row["description"],
                    "industry": row["industry"],
                    "pain_points": row["pain_points"],
                    "technical_level": row["technical_level"],
                    "market_size": row["market_size"],
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