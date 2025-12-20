"""
论文匹配相关路由
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import threading

from api.routes.auth import get_current_user_optional as get_current_user
from services.matching_service import match_papers, match_all
from services.vector_service import get_vector_service
from database.database import get_db_connection, get_user_by_username, save_match_history, get_match_history, get_match_results_by_history_id, get_published_need_by_id
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
    search_text: Optional[str] = ""  # 用户原始搜索文本（用于匹配历史）

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
        
        history_id = None
        
        # 保存匹配历史（使用save_match_history，与找成果保持一致）
        if request.save_match and results:
            try:
                user = get_user_by_username(current_user)
                user_id = user["id"] if user else None
                
                # 构建搜索描述（优先使用用户原始搜索文本，如果没有则使用论文标题）
                search_desc = request.search_text if request.search_text and request.search_text.strip() else (
                    request.paper_title if request.paper_title and request.paper_title.strip() and request.paper_title != "论文" else "成果匹配需求"
                )
                
                # 将需求结果转换为match_results格式（需要适配save_match_history的格式）
                # save_match_history期望results包含title, abstract, score, reason, match_type等字段
                formatted_results = []
                for req in results:
                    formatted_results.append({
                        "paper_id": req.get("requirement_id"),  # 使用requirement_id作为标识
                        "title": req.get("title", ""),
                        "abstract": req.get("description", ""),  # description映射到abstract
                        "authors": "",  # 需求没有作者
                        "categories": req.get("industry", ""),  # industry映射到categories
                        "pdf_url": None,  # 需求没有PDF
                        "published_date": None,
                        "score": req.get("score", 0),
                        "reason": req.get("reason", ""),
                        "match_type": req.get("match_type", ""),
                        "vector_score": req.get("vector_score", 0.0)
                    })
                
                # 使用save_match_history保存，match_mode设为"researcher"（找需求）
                history_id = save_match_history(
                    user_id=user_id,
                    search_desc=search_desc,
                    match_mode="researcher",  # 找需求
                    results=formatted_results
                )
                logger.info(f"匹配历史已保存，历史ID: {history_id}")
            except Exception as e:
                # 保存历史失败不影响匹配结果返回
                logger.error(f"保存匹配历史失败: {e}")
        
        return {
            "requirements": results,
            "total": len(results),
            "history_id": history_id
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
    """获取需求详情（支持系统需求和发布需求）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        requirement_dict = None
        
        # 判断是发布需求还是系统需求
        if requirement_id.startswith("published_need_"):
            # 发布需求：从 published_needs 表查询
            try:
                need_id = int(requirement_id.replace("published_need_", ""))
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的需求ID格式")
            
            need = get_published_need_by_id(need_id)
            if not need:
                raise HTTPException(status_code=404, detail="需求不存在")
            
            # 转换为统一格式，补充系统需求表的字段（发布需求没有这些字段）
            requirement_dict = {
                "requirement_id": requirement_id,  # 使用向量ID格式
                "title": need.get("title", ""),
                "description": need.get("description", ""),
                "industry": need.get("industry", ""),
                "pain_points": "",  # 发布需求没有此字段
                "technical_level": "",  # 发布需求没有此字段
                "market_size": "",  # 发布需求没有此字段
                "contact_info": f"{need.get('contact_name', '')} {need.get('contact_phone', '')}".strip() or need.get("contact_email", ""),
                "source": "published",  # 标记为发布需求
                "company_name": need.get("company_name", ""),
                "contact_name": need.get("contact_name", ""),
                "contact_phone": need.get("contact_phone", ""),
                "contact_email": need.get("contact_email", ""),
                "urgency_level": need.get("urgency_level", ""),
                "budget_range": need.get("budget_range", ""),
                "status": need.get("status", "published"),
                "created_at": need.get("created_at"),
                "updated_at": need.get("updated_at")
            }
        else:
            # 系统需求：从 requirements 表查询
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
            requirement_dict["source"] = "system"  # 标记为系统需求
        
        return requirement_dict
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取需求详情失败: {str(e)}")

@router.post("/match-all", response_model=MatchingResponse)
async def match_all_items(
    request: MatchingRequest,
    current_user: str = Depends(get_current_user)
):
    """
    统一匹配论文和成果接口：
    1. 将用户需求转换为查询向量
    2. 在向量数据库中搜索 Top-K 相似论文和成果
    3. 使用 DeepSeek LLM 对每项进行评分
    4. 按分数排序返回（论文和成果混合）
    5. 可选：保存匹配历史到数据库
    """
    try:
        if not request.requirement or not request.requirement.strip():
            raise HTTPException(status_code=400, detail="需求文本不能为空")
        
        # 调用统一匹配服务
        results = await match_all(
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
                
                # 保存匹配历史（注意：match_results 表可能需要适配成果格式）
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
            "papers": results,  # 虽然字段名是 papers，但实际包含论文和成果
            "total": len(results),
            "history_id": history_id
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
                LIMIT 300
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
    必须验证历史记录属于当前用户
    """
    try:
        # 获取用户ID
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        user_id = user["id"]
        
        # 检查历史记录是否存在且属于当前用户（必须验证用户ID）
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM match_history WHERE id = ? AND user_id = ?", (history_id, user_id))
        history_row = cursor.fetchone()
        conn.close()
        
        if not history_row:
            raise HTTPException(status_code=404, detail="匹配历史不存在或无权限访问")
        
        # 转换为字典
        history = dict(history_row)
        
        # 获取匹配结果
        results = get_match_results_by_history_id(history_id)
        
        # 如果没有匹配结果，返回空列表而不是错误
        if not results:
            return {
                "history_id": history_id,
                "search_desc": history["search_desc"],
                "match_mode": history["match_mode"],
                "match_time": history["created_at"],
                "papers": [],
                "total": 0
            }
        
        # 转换为前端需要的格式
        # 需要区分论文、成果和需求：
        # 1. 如果match_mode是"researcher"（找需求），paper_id是requirement_id，需要查询requirements表
        # 2. 如果paper_id以"achievement_"开头，说明是成果，需要查询published_achievements表
        # 3. 否则是论文
        papers = []
        achievement_ids_to_fetch = []
        achievement_result_map = {}
        requirement_ids_to_fetch = []
        requirement_result_map = {}
        
        is_researcher_mode = history.get("match_mode") == "researcher"
        
        # 先收集需要查询的ID，同时保留原始顺序
        requirement_ids_to_fetch = []
        requirement_result_map = {}
        achievement_ids_to_fetch = []
        achievement_result_map = {}
        
        for result in results:
            paper_id = result.get("paper_id")
            
            # 如果是找需求模式，paper_id实际是requirement_id
            if is_researcher_mode:
                requirement_id = paper_id
                requirement_ids_to_fetch.append(requirement_id)
                requirement_result_map[requirement_id] = result
            # 判断是成果还是论文
            elif paper_id and paper_id.startswith("achievement_"):
                # 这是成果，提取achievement_id
                try:
                    achievement_id = int(paper_id.replace("achievement_", ""))
                    achievement_ids_to_fetch.append(achievement_id)
                    achievement_result_map[achievement_id] = result
                except ValueError:
                    logger.warning(f"无法解析成果ID: {paper_id}")
                    continue
            else:
                # 这是论文，直接添加（保持原有顺序）
                papers.append({
                    "paper_id": paper_id,
                    "title": result.get("title"),
                    "abstract": result.get("abstract"),
                    "authors": result.get("authors"),
                    "published_date": result.get("published_date"),
                    "categories": result.get("categories"),
                    "pdf_url": result.get("pdf_url"),
                    "score": result.get("score"),
                    "reason": result.get("reason"),
                    "match_type": result.get("match_type"),
                    "vector_score": result.get("vector_score"),
                    "item_type": "paper"  # 标记为论文
                })
        
        # 如果是找需求模式，需要查询requirements表和published_needs表获取完整信息
        if requirement_ids_to_fetch:
            # 区分系统需求和发布需求
            system_requirement_ids = [rid for rid in requirement_ids_to_fetch if not rid.startswith("published_need_")]
            published_need_ids = []
            for rid in requirement_ids_to_fetch:
                if rid.startswith("published_need_"):
                    try:
                        need_id = int(rid.replace("published_need_", ""))
                        published_need_ids.append(need_id)
                    except ValueError:
                        logger.warning(f"无法解析发布需求ID: {rid}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            requirement_dict = {}  # 使用字典来存储查询结果，方便按ID查找
            
            # 查询系统需求
            if system_requirement_ids:
                placeholders = ','.join(['?'] * len(system_requirement_ids))
                query = f"SELECT * FROM requirements WHERE requirement_id IN ({placeholders}) AND status = 'active'"
                cursor.execute(query, system_requirement_ids)
                system_requirements = cursor.fetchall()
                for req in system_requirements:
                    req_dict = dict(req)
                    requirement_dict[req_dict["requirement_id"]] = req_dict
            
            # 查询发布需求
            if published_need_ids:
                placeholders = ','.join(['?'] * len(published_need_ids))
                query = f"SELECT * FROM published_needs WHERE id IN ({placeholders}) AND status = 'published'"
                cursor.execute(query, published_need_ids)
                published_needs_raw = cursor.fetchall()
                # 转换发布需求的字段格式
                for need in published_needs_raw:
                    need_dict = dict(need)
                    requirement_id = f"published_need_{need_dict['id']}"
                    requirement_dict[requirement_id] = {
                        "requirement_id": requirement_id,
                        "title": need_dict.get("title", ""),
                        "description": need_dict.get("description", ""),
                        "industry": need_dict.get("industry", ""),
                        "pain_points": "",  # 发布需求没有此字段
                        "technical_level": "",  # 发布需求没有此字段
                        "market_size": "",  # 发布需求没有此字段
                        "_source": "published_need"
                    }
            
            conn.close()
            
            # 按照 requirement_ids_to_fetch 的顺序（即 result_order 的顺序）来构建结果
            for requirement_id in requirement_ids_to_fetch:
                requirement = requirement_dict.get(requirement_id)
                result = requirement_result_map.get(requirement_id)
                if not requirement or not result:
                    continue
                
                papers.append({
                    "paper_id": requirement_id,  # 使用requirement_id作为paper_id（兼容前端）
                    "item_type": "requirement",  # 标记为需求
                    "requirement_id": requirement_id,
                    "title": requirement.get("title") or "",
                    "description": requirement.get("description") or "",
                    "abstract": requirement.get("description") or "",  # 兼容前端，使用abstract字段
                    "industry": requirement.get("industry") or "",
                    "categories": requirement.get("industry") or "",  # 兼容前端，使用categories字段
                    "technical_level": requirement.get("technical_level") or "",
                    "market_size": requirement.get("market_size") or "",
                    "pain_points": requirement.get("pain_points") or "",
                    "pdf_url": None,  # 需求没有PDF
                    "authors": "",  # 需求没有作者
                    "published_date": None,
                    "score": result.get("score"),
                    "reason": result.get("reason"),
                    "match_type": result.get("match_type"),
                    "vector_score": result.get("vector_score"),
                    "implementation_suggestion": result.get("implementation_suggestion")
                })
        
        # 如果有成果，需要查询published_achievements表获取完整信息
        if achievement_ids_to_fetch:
            conn = get_db_connection()
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(achievement_ids_to_fetch))
            query = f"SELECT * FROM published_achievements WHERE id IN ({placeholders}) AND status = 'published'"
            cursor.execute(query, achievement_ids_to_fetch)
            achievements_raw = cursor.fetchall()
            conn.close()
            
            # 转换为字典，方便按ID查找
            achievement_dict = {}
            for achievement in achievements_raw:
                achievement_dict[achievement["id"]] = dict(achievement)
            
            # 按照 achievement_ids_to_fetch 的顺序（即 result_order 的顺序）来构建结果
            for achievement_id in achievement_ids_to_fetch:
                achievement = achievement_dict.get(achievement_id)
                result = achievement_result_map.get(achievement_id)
                if not achievement or not result:
                    continue
                
                # 解析cooperation_mode JSON字段
                cooperation_mode = []
                if achievement.get('cooperation_mode'):
                    try:
                        import json
                        cooperation_mode = json.loads(achievement['cooperation_mode'])
                    except:
                        pass
                
                # 确保 title 和 abstract 字段不为空（兼容旧数据）
                achievement_name = achievement.get("name") or ""
                achievement_description = achievement.get("description") or ""
                
                papers.append({
                    "paper_id": f"achievement_{achievement_id}",
                    "item_type": "achievement",  # 标记为成果
                    "achievement_id": achievement_id,
                    "name": achievement_name,
                    "title": achievement_name,  # 兼容前端，使用title字段
                    "description": achievement_description,
                    "abstract": achievement_description,  # 兼容前端，使用abstract字段
                    "application": achievement.get("application") or "",
                    "field": achievement.get("field") or "",
                    "categories": achievement.get("field") or "",  # 兼容前端，使用categories字段
                    "cooperation_mode": cooperation_mode,
                    "contact_name": achievement.get("contact_name") or "",
                    "contact_phone": achievement.get("contact_phone") or "",
                    "contact_email": achievement.get("contact_email") or "",
                    "pdf_url": None,  # 成果没有PDF
                    "authors": "",  # 成果没有作者
                    "published_date": None,
                    "score": result.get("score"),
                    "reason": result.get("reason"),
                    "match_type": result.get("match_type"),
                    "vector_score": result.get("vector_score")
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

