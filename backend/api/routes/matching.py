"""
论文匹配相关路由
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
import threading

from api.routes.auth import get_current_user_optional as get_current_user
from services.matching_service import match_papers
from services.vector_service import get_vector_service
from database.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# 索引任务状态管理
_indexer_running = False
_indexer_progress = {
    "status": "idle",  # idle, running, completed, error
    "total": 0,
    "processed": 0,
    "skipped": 0,
    "error": 0,
    "message": ""
}
_indexer_lock = threading.Lock()

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
    将数据库中未向量化的论文索引到向量数据库
    这是一个后台任务，会立即返回
    """
    global _indexer_running, _indexer_progress
    
    # 检查是否已有任务在运行
    with _indexer_lock:
        if _indexer_running:
            raise HTTPException(status_code=400, detail="索引任务正在运行中，请稍后再试")
        
        _indexer_running = True
        _indexer_progress = {
            "status": "running",
            "total": 0,
            "processed": 0,
            "skipped": 0,
            "error": 0,
            "message": "正在初始化..."
        }
    
    def _index_papers():
        """后台任务：索引论文"""
        global _indexer_running, _indexer_progress
        
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
            
            total_papers = len(papers)
            
            with _indexer_lock:
                _indexer_progress["total"] = total_papers
                _indexer_progress["message"] = f"找到 {total_papers} 篇论文，开始索引..."
            
            logger.info(f"找到 {total_papers} 篇论文需要索引")
            
            if not papers:
                with _indexer_lock:
                    _indexer_progress["status"] = "completed"
                    _indexer_progress["message"] = "数据库中没有论文，请先运行爬虫"
                logger.warning("数据库中没有论文，请先运行爬虫")
                _indexer_running = False
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
            
            for idx, paper in enumerate(papers):
                try:
                    arxiv_id = paper["arxiv_id"]
                    title = paper["title"]
                    abstract = paper["abstract"] or ""
                    
                    if not title or not arxiv_id:
                        skipped_count += 1
                        continue
                    
                    # 添加到向量数据库（内部会检查是否已存在）
                    added = vector_service.add_paper(arxiv_id, title, abstract)
                    if added:
                        processed_count += 1
                    else:
                        skipped_count += 1
                    
                    # 更新进度
                    with _indexer_lock:
                        _indexer_progress["processed"] = processed_count
                        _indexer_progress["skipped"] = skipped_count
                        _indexer_progress["error"] = error_count
                        _indexer_progress["message"] = f"已处理 {idx + 1}/{total_papers} 篇论文..."
                    
                    if processed_count % 10 == 0:
                        logger.info(f"已处理 {processed_count} 篇论文...")
                        
                except Exception as e:
                    error_count += 1
                    paper_id = paper["arxiv_id"] if "arxiv_id" in paper.keys() else 'unknown'
                    logger.error(f"处理论文 {paper_id} 失败: {str(e)}")
                    with _indexer_lock:
                        _indexer_progress["error"] = error_count
                    continue
            
            final_count = vector_service.get_paper_count()
            
            with _indexer_lock:
                _indexer_progress["status"] = "completed"
                _indexer_progress["message"] = f"索引完成！成功: {processed_count} 篇，跳过: {skipped_count} 篇，失败: {error_count} 篇"
            
            logger.info(f"索引完成！")
            logger.info(f"  - 成功处理: {processed_count} 篇")
            logger.info(f"  - 跳过（已存在）: {skipped_count} 篇")
            logger.info(f"  - 处理失败: {error_count} 篇")
            logger.info(f"  - 向量数据库总数: {final_count} 篇")
            
        except Exception as e:
            with _indexer_lock:
                _indexer_progress["status"] = "error"
                _indexer_progress["message"] = f"索引过程失败: {str(e)}"
            logger.error(f"索引过程失败: {str(e)}")
        finally:
            _indexer_running = False
    
    # 添加到后台任务
    background_tasks.add_task(_index_papers)
    
    return {
        "message": "索引任务已在后台启动",
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
        
        # 获取索引任务状态
        with _indexer_lock:
            indexer_status = _indexer_progress.copy()
        
        return {
            "vector_db_count": count,
            "database_count": db_total,
            "indexed_percentage": round(count / db_total * 100, 2) if db_total > 0 else 0,
            "unindexed_count": db_total - count,
            "indexer_status": indexer_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@router.get("/index-status")
async def get_index_status(current_user: str = Depends(get_current_user)):
    """获取索引任务状态"""
    with _indexer_lock:
        return _indexer_progress.copy()

