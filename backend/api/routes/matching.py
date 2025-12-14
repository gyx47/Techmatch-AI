"""
论文匹配相关路由
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import threading

from api.routes.auth import get_current_user_optional as get_current_user
from services.matching_service import match_papers
from services.vector_service import get_vector_service
from database.database import get_db_connection, get_user_by_username, save_match_history, get_match_history, get_match_results_by_history_id
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
    match_mode: str = "enterprise"  # 匹配模式：enterprise（企业找成果）或 researcher（专家找需求）
    save_history: bool = True  # 是否保存匹配历史

class MatchingResponse(BaseModel):
    papers: List[dict]
    total: int
    history_id: Optional[int] = None  # 如果保存了历史，返回历史ID

class PaperToRequirementRequest(BaseModel):
    paper_title: str  # 论文标题
    paper_abstract: str  # 论文摘要
    paper_categories: Optional[str] = ""  # 论文分类
    top_k: int = 20  # 返回的需求数量
    save_match: bool = True  # 是否保存匹配记录

class RequirementResponse(BaseModel):
    requirement_id: str
    title: str
    description: str
    industry: str
    pain_points: str
    technical_level: str
    market_size: str
    score: float
    reason: str
    match_type: str
    implementation_suggestion: str
    vector_score: float

class PaperToRequirementResponse(BaseModel):
    requirements: List[RequirementResponse]
    total: int
    match_id: Optional[int] = None

class RequirementCreate(BaseModel):
    requirement_id: str  # 需求ID（可自定义）
    title: str  # 需求标题
    description: str  # 详细描述
    industry: str  # 行业
    pain_points: str  # 痛点
    technical_level: str = "medium"  # 技术难度
    market_size: str = "medium"  # 市场规模
    contact_info: Optional[str] = None  # 联系信息

@router.post("/paper-to-requirements", response_model=PaperToRequirementResponse)
async def match_paper_to_requirements(
    request: PaperToRequirementRequest,
    current_user: str = Depends(get_current_user)
):
    """
    科研成果匹配需求接口
    输入：论文信息 → 输出：匹配的企业需求
    """
    try:
        # 导入新的匹配服务
        from services.requirement_matching_service import match_requirements_for_paper
        
        # 调用匹配服务
        results = await match_requirements_for_paper(
            paper_title=request.paper_title,
            paper_abstract=request.paper_abstract,
            paper_categories=request.paper_categories,
            top_k=request.top_k
        )
        
        match_id = None
        
        # 保存匹配记录
        if request.save_match and results:
            try:
                user = get_user_by_username(current_user)
                user_id = user["id"] if user else None
                
                # 保存到新的匹配表
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO paper_to_requirement_matches 
                    (user_id, paper_id, paper_title, requirement_ids, match_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    "custom_paper",  # 如果没有arxiv_id
                    request.paper_title[:100],
                    ",".join([r["requirement_id"] for r in results]),
                    len(results)
                ))
                
                match_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                logger.info(f"论文→需求匹配记录已保存，ID: {match_id}")
            except Exception as e:
                logger.error(f"保存匹配记录失败: {e}")
        
        return {
            "requirements": results,
            "total": len(results),
            "match_id": match_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"需求匹配失败: {str(e)}")
        
@router.post("/requirements")
async def create_requirement(
    requirement: RequirementCreate,
    current_user: str = Depends(get_current_user)
):
    """创建新需求（同时向量化）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("SELECT id FROM requirements WHERE requirement_id = ?", 
                      (requirement.requirement_id,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="需求ID已存在")
        
        # 插入数据库
        cursor.execute("""
            INSERT INTO requirements 
            (requirement_id, title, description, industry, pain_points, 
             technical_level, market_size, contact_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            requirement.requirement_id,
            requirement.title,
            requirement.description,
            requirement.industry,
            requirement.pain_points,
            requirement.technical_level,
            requirement.market_size,
            requirement.contact_info
        ))
        
        conn.commit()
        conn.close()
        
        # 向量化需求
        vector_service = get_vector_service()
        vector_service.add_requirement(
            requirement_id=requirement.requirement_id,
            title=requirement.title,
            description=requirement.description,
            industry=requirement.industry,
            pain_points=requirement.pain_points
        )
        
        return {"message": "需求创建成功", "requirement_id": requirement.requirement_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建需求失败: {str(e)}")

@router.get("/requirements")
async def list_requirements(
    page: int = 1,
    page_size: int = 20,
    industry: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """获取需求列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        query = "SELECT * FROM requirements WHERE status = 'active'"
        params = []
        
        if industry:
            query += " AND industry LIKE ?"
            params.append(f"%{industry}%")
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        cursor.execute(query, params)
        requirements = [dict(row) for row in cursor.fetchall()]
        
        # 获取总数
        cursor.execute("SELECT COUNT(*) as total FROM requirements WHERE status = 'active'")
        total = cursor.fetchone()['total']
        
        conn.close()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "requirements": requirements
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取需求列表失败: {str(e)}")
    

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
    5. 可选：保存匹配历史到数据库
    """
    try:
        if not request.requirement or not request.requirement.strip():
            raise HTTPException(status_code=400, detail="需求文本不能为空")
        
        # 调用匹配服务
        results = await match_papers(
            user_requirement=request.requirement,
            top_k=request.top_k
        )
        
        history_id = None
        
        # 如果启用保存历史，保存到数据库
        if request.save_history and results:
            try:
                # 获取用户ID
                user = get_user_by_username(current_user)
                user_id = user["id"] if user else None
                
                # 保存匹配历史
                history_id = save_match_history(
                    user_id=user_id,
                    search_desc=request.requirement,
                    match_mode=request.match_mode,
                    results=results
                )
                logger.info(f"匹配历史已保存，历史ID: {history_id}")
            except Exception as e:
                # 保存历史失败不影响匹配结果返回
                logger.error(f"保存匹配历史失败: {e}")
        
        return {
            "papers": results,
            "total": len(results),
            "history_id": history_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匹配失败: {str(e)}")
    
@router.get("/requirements/{requirement_id}")
async def get_requirement_detail(
    requirement_id: str,
    current_user: str = Depends(get_current_user)
):
    """获取需求详情"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取需求基本信息
        cursor.execute("""
            SELECT * FROM requirements 
            WHERE requirement_id = ? AND status = 'active'
        """, (requirement_id,))
        
        requirement = cursor.fetchone()
        conn.close()
        
        if not requirement:
            raise HTTPException(status_code=404, detail="需求不存在")
        
        # 转换为字典
        requirement_dict = dict(requirement)
        
        return requirement_dict
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取需求详情失败: {str(e)}")

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
                LIMIT 100
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
        
        # 检查集合健康状态
        health = vector_service.check_collection_health()
        
        if not health["healthy"]:
            # 集合损坏，返回错误信息
            error_msg = health["error"]
            is_corrupted = 'Cannot open header file' in error_msg or 'header file' in error_msg.lower()
            
            # 获取数据库中的论文总数（即使向量数据库损坏也能获取）
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM papers WHERE arxiv_id IS NOT NULL")
            db_total = cursor.fetchone()["total"]
            conn.close()
            
            return {
                "vector_db_count": 0,
                "database_count": db_total,
                "indexed_percentage": 0,
                "unindexed_count": db_total,
                "healthy": False,
                "error": error_msg,
                "is_corrupted": is_corrupted,
                "fix_suggestion": "请运行修复脚本: python backend/scripts/fix_chromadb.py" if is_corrupted else None,
                "indexer_status": {"status": "idle"}
            }
        
        count = health["count"]
        
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
            "healthy": True,
            "indexer_status": indexer_status
        }
    except Exception as e:
        error_msg = str(e)
        is_corrupted = 'Cannot open header file' in error_msg or 'header file' in error_msg.lower()
        raise HTTPException(
            status_code=500, 
            detail={
                "message": f"获取统计信息失败: {error_msg}",
                "is_corrupted": is_corrupted,
                "fix_suggestion": "请运行修复脚本: python backend/scripts/fix_chromadb.py" if is_corrupted else None
            }
        )

@router.get("/history")
async def get_match_history_list(
    page: int = 1,
    page_size: int = 20,
    current_user: str = Depends(get_current_user)
):
    """
    获取匹配历史列表
    """
    try:
        # 获取用户ID
        user = get_user_by_username(current_user)
        user_id = user["id"] if user else None
        
        # 获取匹配历史
        history_data = get_match_history(user_id=user_id, page=page, page_size=page_size)
        
        # 格式化返回数据
        items = []
        for item in history_data["items"]:
            items.append({
                "history_id": item["id"],
                "search_desc": item["search_desc"],
                "match_mode": item["match_mode"],
                "match_type": "找成果" if item["match_mode"] == "enterprise" else "找需求",
                "result_count": item["result_count"],
                "match_time": item["created_at"]
            })
        
        return {
            "total": history_data["total"],
            "page": history_data["page"],
            "page_size": history_data["page_size"],
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取匹配历史失败: {str(e)}")

@router.get("/history/{history_id}/results")
async def get_match_history_results(
    history_id: int,
    current_user: str = Depends(get_current_user)
):
    """
    根据历史ID获取匹配结果详情
    """
    try:
        # 验证历史记录是否属于当前用户
        user = get_user_by_username(current_user)
        user_id = user["id"] if user else None
        
        # 检查历史记录是否存在且属于当前用户
        conn = get_db_connection()
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM match_history WHERE id = ? AND user_id = ?", (history_id, user_id))
        else:
            cursor.execute("SELECT * FROM match_history WHERE id = ?", (history_id,))
        history = cursor.fetchone()
        conn.close()
        
        if not history:
            raise HTTPException(status_code=404, detail="匹配历史不存在")
        
        # 获取匹配结果
        results = get_match_results_by_history_id(history_id)
        
        # 转换为前端需要的格式
        papers = []
        for result in results:
            papers.append({
                "paper_id": result["paper_id"],
                "title": result["title"],
                "abstract": result["abstract"],
                "authors": result["authors"],
                "published_date": result["published_date"],
                "categories": result["categories"],
                "pdf_url": result["pdf_url"],
                "score": result["score"],
                "reason": result["reason"],
                "match_type": result["match_type"],
                "vector_score": result["vector_score"]
            })
        
        return {
            "history_id": history_id,
            "search_desc": history["search_desc"],
            "match_mode": history["match_mode"],
            "match_time": history["created_at"],
            "papers": papers,
            "total": len(papers)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取匹配结果失败: {str(e)}")

@router.get("/index-status")
async def get_index_status(current_user: str = Depends(get_current_user)):
    """获取索引任务状态"""
    with _indexer_lock:
        return _indexer_progress.copy()

