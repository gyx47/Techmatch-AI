"""
论文匹配相关路由
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List

from api.routes.auth import get_current_user_optional as get_current_user
from services.matching_service import match_papers
from services.vector_service import get_vector_service
from database.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class MatchingRequest(BaseModel):
    requirement: str  # 用户需求文本
    top_k: int = 50   # 返回的论文数量

class MatchingResponse(BaseModel):
    papers: List[dict]
    total: int

@router.post("/match", response_model=MatchingResponse)
async def match_user_requirement(
    request: MatchingRequest,
    current_user: str = Depends(get_current_user)
):
    """
    匹配论文接口：
    1. 将用户需求转换为查询向量
    2. 在向量数据库中搜索 Top-K 相似论文
    3. 使用 DeepSeek LLM 对每篇论文进行评分
    4. 按分数排序返回
    """
    try:
        if not request.requirement or not request.requirement.strip():
            raise HTTPException(status_code=400, detail="需求文本不能为空")
        
        # 调用匹配服务
        results = await match_papers(
            user_requirement=request.requirement,
            top_k=request.top_k
        )
        
        return {
            "papers": results,
            "total": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匹配失败: {str(e)}")

@router.post("/index-papers")
async def index_existing_papers(
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """
    将数据库中已有的论文索引到向量数据库
    这是一个后台任务，会立即返回
    """
    def _index_papers():
        """后台任务：索引论文"""
        try:
            # 获取数据库连接
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 获取所有论文
            cursor.execute("""
                SELECT arxiv_id, title, abstract 
                FROM papers 
                WHERE arxiv_id IS NOT NULL 
                AND title IS NOT NULL
                ORDER BY created_at DESC
            """)
            
            papers = cursor.fetchall()
            conn.close()
            
            logger.info(f"找到 {len(papers)} 篇论文需要索引")
            
            if not papers:
                logger.warning("数据库中没有论文，请先运行爬虫")
                return
            
            # 获取向量服务
            vector_service = get_vector_service()
            
            # 检查向量数据库中已有的论文
            existing_count = vector_service.get_paper_count()
            logger.info(f"向量数据库中已有 {existing_count} 篇论文")
            
            # 处理每篇论文
            processed_count = 0
            skipped_count = 0
            error_count = 0
            
            for paper in papers:
                try:
                    arxiv_id = paper["arxiv_id"]
                    title = paper["title"]
                    abstract = paper["abstract"] or ""
                    
                    if not title or not arxiv_id:
                        skipped_count += 1
                        continue
                    
                    # 检查是否已存在
                    try:
                        results = vector_service.collection.get(ids=[arxiv_id])
                        if results and results.get('ids') and len(results['ids']) > 0:
                            skipped_count += 1
                            continue
                    except:
                        pass  # 不存在，继续添加
                    
                    # 添加到向量数据库
                    vector_service.add_paper(arxiv_id, title, abstract)
                    processed_count += 1
                    
                    if processed_count % 10 == 0:
                        logger.info(f"已处理 {processed_count} 篇论文...")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理论文 {paper.get('arxiv_id', 'unknown')} 失败: {str(e)}")
                    continue
            
            logger.info(f"索引完成！")
            logger.info(f"  - 成功处理: {processed_count} 篇")
            logger.info(f"  - 跳过（已存在）: {skipped_count} 篇")
            logger.info(f"  - 处理失败: {error_count} 篇")
            logger.info(f"  - 向量数据库总数: {vector_service.get_paper_count()} 篇")
            
        except Exception as e:
            logger.error(f"索引过程失败: {str(e)}")
            raise
    
    # 添加到后台任务
    background_tasks.add_task(_index_papers)
    
    return {
        "message": "索引任务已在后台启动，请查看日志了解进度",
        "status": "started"
    }

@router.get("/vector-stats")
async def get_vector_stats(current_user: str = Depends(get_current_user)):
    """获取向量数据库统计信息"""
    try:
        vector_service = get_vector_service()
        count = vector_service.get_paper_count()
        
        # 获取数据库中的论文总数
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM papers WHERE arxiv_id IS NOT NULL")
        db_total = cursor.fetchone()["total"]
        conn.close()
        
        return {
            "vector_db_count": count,
            "database_count": db_total,
            "indexed_percentage": round(count / db_total * 100, 2) if db_total > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

