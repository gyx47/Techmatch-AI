"""
需求匹配服务 - 科研成果找需求（调试版）
"""
import logging
from typing import List, Dict
from database.database import get_db_connection
from services.vector_service import get_vector_service
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

async def match_requirements_for_paper(
    paper_title: str, 
    paper_abstract: str,
    paper_categories: str = "",
    top_k: int = 20
) -> List[Dict]:
    """
    为科研成果匹配需求
    """
    logger.info("=" * 50)
    logger.info("开始需求匹配流程")
    logger.info(f"论文标题: {paper_title[:50]}...")
    logger.info(f"论文摘要长度: {len(paper_abstract)} 字符")
    logger.info(f"论文分类: {paper_categories}")
    logger.info("=" * 50)
    
    try:
        llm_service = get_llm_service()
        vector_service = get_vector_service()
        
        # ---------------------------------------------------------
        # 步骤 1: 论文应用场景扩展
        # ---------------------------------------------------------
        logger.info("步骤1: 论文应用场景扩展...")
        try:
            application_scenarios = await llm_service.expand_paper_to_scenarios(
                paper_title, paper_abstract
            )
            logger.info(f"应用场景扩展结果: {application_scenarios[:100]}...")
        except Exception as e:
            logger.error(f"应用场景扩展失败: {e}")
            application_scenarios = "通用技术"
        
        # ---------------------------------------------------------
        # 步骤 2: 向量搜索相似需求
        # ---------------------------------------------------------
        search_text = f"{paper_title}\n{paper_abstract}\n应用场景:{application_scenarios}"
        logger.info(f"步骤2: 向量搜索相似需求...")
        logger.info(f"搜索文本长度: {len(search_text)} 字符")
        
        similar_requirements = vector_service.search_requirements(search_text, top_k=top_k)
        logger.info(f"向量搜索返回: {len(similar_requirements)} 个需求")
        
        if not similar_requirements:
            logger.warning("向量搜索返回空列表，检查需求库是否为空")
            # 检查需求库数量
            try:
                health = vector_service.check_collection_health()
                logger.info(f"向量库状态: {health}")
                if hasattr(vector_service, 'get_requirement_count'):
                    count = vector_service.get_requirement_count()
                    logger.info(f"需求库数量: {count}")
            except Exception as e:
                logger.error(f"检查向量库状态失败: {e}")
            return []
        
        # 打印前几个结果
        for i, (req_id, score) in enumerate(similar_requirements[:3]):
            logger.info(f"匹配需求 {i+1}: ID={req_id}, 相似度={score:.4f}")
        
        # ---------------------------------------------------------
        # 步骤 3: 获取需求详情
        # ---------------------------------------------------------
        requirement_ids = [r[0] for r in similar_requirements]
        logger.info(f"步骤3: 获取需求详情，ID列表: {requirement_ids[:5]}...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 一次性获取所有需求详情
        placeholders = ','.join(['?'] * len(requirement_ids))
        query = f"""
            SELECT * FROM requirements 
            WHERE requirement_id IN ({placeholders}) 
            AND status = 'active'
        """
        logger.debug(f"执行SQL: {query}")
        logger.debug(f"参数: {requirement_ids}")
        
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
        for i, req in enumerate(requirement_details[:2]):
            logger.info(f"需求详情 {i+1}: {req['title'][:30]}... (行业: {req['industry']})")
        
        # ---------------------------------------------------------
        # 步骤 4: LLM评估论文与需求的匹配度
        # ---------------------------------------------------------
        logger.info(f"步骤4: LLM评估匹配度，候选需求数量: {len(requirement_details)}")
        
        if not requirement_details:
            logger.warning("没有可评估的需求详情")
            return []
        
        try:
            ranked_results = await llm_service.score_requirements_for_paper(
                paper_title=paper_title,
                paper_abstract=paper_abstract,
                paper_categories=paper_categories,
                requirements=requirement_details
            )
            logger.info(f"LLM评估返回 {len(ranked_results)} 个结果")
        except Exception as e:
            logger.error(f"LLM评估失败: {e}")
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
        
        logger.info(f"最终输出 {len(final_output)} 个结果")
        logger.info("=" * 50)
        logger.info("需求匹配流程完成")
        logger.info("=" * 50)
        
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