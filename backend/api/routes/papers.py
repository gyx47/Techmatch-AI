"""
论文相关路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, Request
from typing import List, Optional, Tuple, Dict, Any
import pydantic as pydantic
import requests
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
import time
from database.database import (
    save_paper,
    get_papers_by_query,
    get_papers_by_query_paginated,
    get_db_connection,
    get_user_by_username,
    save_implementation_path_history,
    get_implementation_path_history_by_history_id,
    get_all_implementation_path_history,
)
from api.routes.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

from services.pdf import get_pdf_service
from services.llm_service import get_llm_service

# =======================
# 全局实现路径进度状态（本地模式）
# =======================
# key: task_id, value: 进度信息
implementation_progress: Dict[str, Dict[str, Any]] = {}

class PaperResponse(pydantic.BaseModel):
    arxiv_id: str
    title: str
    authors: str
    abstract: str
    published_date: str
    categories: str
    pdf_url: str

def parse_arxiv_response(xml_content: str) -> List[dict]:
    """解析arXiv API响应"""
    papers = []
    try:
        root = ET.fromstring(xml_content)
        
        for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
            paper = {}
            
            # 获取arXiv ID
            arxiv_id = entry.find('.//{http://arxiv.org/schemas/atom}id')
            if arxiv_id is not None:
                paper['arxiv_id'] = arxiv_id.text.split('/')[-1]
            
            # 获取标题
            title = entry.find('.//{http://www.w3.org/2005/Atom}title')
            if title is not None:
                paper['title'] = title.text.strip()
            
            # 获取作者
            authors = []
            for author in entry.findall('.//{http://www.w3.org/2005/Atom}author'):
                name = author.find('.//{http://www.w3.org/2005/Atom}name')
                if name is not None:
                    authors.append(name.text)
            paper['authors'] = ', '.join(authors)
            
            # 获取摘要
            summary = entry.find('.//{http://www.w3.org/2005/Atom}summary')
            if summary is not None:
                paper['abstract'] = summary.text.strip()
            
            # 获取发布日期
            published = entry.find('.//{http://www.w3.org/2005/Atom}published')
            if published is not None:
                paper['published_date'] = published.text[:10]  # 只取日期部分
            
            # 获取分类
            categories = []
            for category in entry.findall('.//{http://arxiv.org/schemas/atom}primary_category'):
                if category.get('term'):
                    categories.append(category.get('term'))
            paper['categories'] = ', '.join(categories)
            
            # 生成PDF URL
            if paper.get('arxiv_id'):
                paper['pdf_url'] = f"https://arxiv.org/pdf/{paper['arxiv_id']}.pdf"
            
            papers.append(paper)
            
    except ET.ParseError as e:
        print(f"XML解析错误: {e}")
    
    return papers

@router.get("/search", response_model=List[PaperResponse])
async def search_papers(
    query: str = Query(..., description="搜索关键词"),
    max_results: int = Query(20, description="最大结果数量"),
    current_user: str = Depends(get_current_user)
):
    """搜索论文"""
    try:
        # 构建arXiv API请求URL
        base_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        # 发送请求到arXiv API
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        
        # 解析响应
        papers = parse_arxiv_response(response.text)
        
        # 保存论文到数据库
        for paper in papers:
            try:
                save_paper(paper)
            except Exception as e:
                print(f"保存论文失败: {e}")
        
        return papers
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"搜索请求失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索处理失败: {str(e)}")

@router.get("/local-search")
async def local_search_papers(
    query: str = Query("", description="搜索关键词（可选）"),
    limit: Optional[int] = Query(None, description="结果数量限制（向后兼容，如果提供则忽略分页参数）"),
    page: Optional[int] = Query(None, ge=1, description="页码"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="每页数量"),
    current_user: str = Depends(get_current_user)
):
    """本地数据库搜索论文（支持分页）"""
    try:
        # 如果提供了 limit 参数（向后兼容），使用 limit，返回数组
        if limit is not None:
            papers = get_papers_by_query(query, limit)
            return papers
        else:
            # 使用分页，返回分页格式
            page_num = page if page is not None else 1
            page_size_num = page_size if page_size is not None else 20
            result = get_papers_by_query_paginated(query, page_num, page_size_num)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"本地搜索失败: {str(e)}")

@router.get("/categories")
async def get_categories():
    """获取论文分类列表"""
    categories = [
        "cs.AI", "cs.CL", "cs.CC", "cs.CE", "cs.CG", "cs.GT", "cs.CV", "cs.CY",
        "cs.CR", "cs.DS", "cs.DB", "cs.DL", "cs.DM", "cs.DC", "cs.ET", "cs.FL",
        "cs.GL", "cs.GR", "cs.AR", "cs.HC", "cs.IR", "cs.IT", "cs.LG", "cs.LO",
        "cs.MS", "cs.MA", "cs.MM", "cs.NI", "cs.NE", "cs.NA", "cs.OS", "cs.OH",
        "cs.PF", "cs.PL", "cs.RO", "cs.SI", "cs.SE", "cs.SD", "cs.SC", "cs.SY"
    ]
    return {"categories": categories}

class GeneratePathRequest(pydantic.BaseModel):
    """生成实现路径的请求"""
    paper_ids: List[str]  # 论文的arxiv_id列表
    user_requirement: Optional[str] = None  # 用户需求描述（可选，如果提供history_id则从历史获取）
    history_id: Optional[int] = None  # 匹配历史ID（可选，如果提供则从历史获取需求）
    max_pages_per_paper: int = 20  # 每篇论文最大提取页数
    # 由前端生成的任务ID，用于实时查询进度（例如 Date.now().toString()）
    task_id: Optional[str] = None

class PaperAnalysisResponse(pydantic.BaseModel):
    """论文分析结果"""
    arxiv_id: str
    title: str
    analysis: dict
    status: str  # success, error
    error_message: Optional[str] = None
    # timings 中记录该论文从 PDF 解析到 LLM 精读的耗时（毫秒）
    timings: Optional[Dict[str, Any]] = None

class ImplementationPathResponse(pydantic.BaseModel):
    """实现路径响应"""
    papers_analysis: List[PaperAnalysisResponse]
    implementation_path: dict
    status: str  # success, error
    error_message: Optional[str] = None
    # timings 记录整体耗时信息：包括各阶段耗时和总耗时（毫秒）
    timings: Optional[Dict[str, Any]] = None


async def process_paper(
    pdf_service: "PDFService",  # pyright: ignore[reportUndefinedVariable]
    llm_service: "LLMService",  # pyright: ignore[reportUndefinedVariable]
    paper: dict,
    user_requirement: str,
    max_pages_per_paper: int,
    task_id: Optional[str] = None,
) -> Tuple[PaperAnalysisResponse, Optional[dict]]:
    """
    并发处理单篇论文：下载 PDF + 调用 LLM 进行精读分析

    返回：
        - PaperAnalysisResponse：用于直接返回给前端的单篇分析结果
        - dict | None：用于后续生成实现路径的精简数据
    """
    arxiv_id = paper["arxiv_id"]
    title = paper["title"]
    abstract = paper.get("abstract", "")
    pdf_url = paper.get("pdf_url", f"https://arxiv.org/pdf/{arxiv_id}.pdf")

    try:
        # 检查是否已取消（开始处理前）
        if task_id and task_id in implementation_progress and implementation_progress[task_id].get("status") == "cancelled":
            logger.info(f"任务 {task_id} 已取消，跳过论文 {arxiv_id}")
            raise asyncio.CancelledError("任务已取消")
            
        logger.info(f"开始分析论文: {title} ({arxiv_id})")

        # ==============================
        # 1. 下载 / 解析 PDF（在线程池中）
        # ==============================
        t_pdf_start = time.perf_counter()
        # pdf_content = await asyncio.to_thread(
        #     pdf_service.get_paper_content,
        #     pdf_url,
        #     arxiv_id,
        #     max_pages=max_pages_per_paper,
        # )
        pdf_content = await pdf_service.get_paper_content(pdf_url, arxiv_id, max_pages_per_paper)
        t_pdf_end = time.perf_counter()
        pdf_duration_ms = int((t_pdf_end - t_pdf_start) * 1000)

        # 检查是否已取消（PDF 解析后）
        if task_id and task_id in implementation_progress and implementation_progress[task_id].get("status") == "cancelled":
            logger.info(f"任务 {task_id} 已取消，停止处理论文 {arxiv_id}")
            raise asyncio.CancelledError("任务已取消")

        # 更新进度：PDF 阶段完成（或失败时也记录耗时）
        if task_id and task_id in implementation_progress:
            paper_progress = implementation_progress[task_id]["papers"].get(arxiv_id)
            if paper_progress is not None:
                paper_progress["timings"]["pdf_ms"] = pdf_duration_ms
                paper_progress["status"] = "pdf_done" if pdf_content else "pdf_failed"

        if not pdf_content:
            logger.warning(
                f"论文 {arxiv_id} PDF 获取失败，耗时 {pdf_duration_ms} ms"
            )
            return (
                PaperAnalysisResponse(
                    arxiv_id=arxiv_id,
                    title=title,
                    analysis={},
                    status="error",
                    error_message="无法获取PDF内容",
                    timings={
                        "pdf_ms": pdf_duration_ms,
                        "llm_ms": None,
                        "total_ms": pdf_duration_ms,
                    },
                ),
                None,
            )

        # 检查是否已取消
        if task_id and task_id in implementation_progress and implementation_progress[task_id].get("status") == "cancelled":
            logger.info(f"任务 {task_id} 已取消，停止处理论文 {arxiv_id}")
            raise asyncio.CancelledError("任务已取消")

        # ==============================
        # 2. LLM 精读分析
        # ==============================
        t_llm_start = time.perf_counter()
        logger.info(f"开始 LLM 精读分析: {arxiv_id}")
        analysis = await llm_service.analyze_paper_with_router(
            paper_title=title,
            paper_abstract=abstract,
            pdf_content=pdf_content,
            user_requirement=user_requirement,
        )
        
        # 检查是否已取消（LLM 分析后）
        if task_id and task_id in implementation_progress and implementation_progress[task_id].get("status") == "cancelled":
            logger.info(f"任务 {task_id} 已取消，停止处理论文 {arxiv_id}")
            raise asyncio.CancelledError("任务已取消")
        t_llm_end = time.perf_counter()
        # 使用 round 而不是 int，确保至少显示 1ms（如果耗时 < 1ms）
        llm_duration_ms = max(1, round((t_llm_end - t_llm_start) * 1000))
        logger.info(f"LLM 精读分析完成: {arxiv_id}, 耗时: {llm_duration_ms} ms")

        total_ms = pdf_duration_ms + llm_duration_ms
        logger.info(
            f"论文 {arxiv_id} 分析完成：PDF解析 {pdf_duration_ms} ms，"
            f"LLM 精读 {llm_duration_ms} ms，总计 {total_ms} ms"
        )

        # 更新进度：LLM 阶段完成
        if task_id and task_id in implementation_progress:
            paper_progress = implementation_progress[task_id]["papers"].get(arxiv_id)
            if paper_progress is not None:
                paper_progress["timings"]["llm_ms"] = llm_duration_ms
                paper_progress["timings"]["total_ms"] = total_ms
                paper_progress["status"] = "done"

        if "error" in analysis:
            return (
                PaperAnalysisResponse(
                    arxiv_id=arxiv_id,
                    title=title,
                    analysis={},
                    status="error",
                    error_message=analysis.get("error", "分析失败"),
                    timings={
                        "pdf_ms": pdf_duration_ms,
                        "llm_ms": llm_duration_ms,
                        "total_ms": total_ms,
                    },
                ),
                None,
            )

        # 成功分析
        summary_data = {
            "paper_title": title,
            "paper_abstract": abstract,
            "analysis": analysis,
            "timings": {
                "pdf_ms": pdf_duration_ms,
                "llm_ms": llm_duration_ms,
                "total_ms": total_ms,
            },
        }

        return (
            PaperAnalysisResponse(
                arxiv_id=arxiv_id,
                title=title,
                analysis=analysis,
                status="success",
                timings={
                    "pdf_ms": pdf_duration_ms,
                    "llm_ms": llm_duration_ms,
                    "total_ms": total_ms,
                },
            ),
            summary_data,
        )

    except asyncio.CancelledError:
        # 任务已取消，直接抛出，让上层处理
        raise
    except Exception as e:
        logger.error(f"分析论文失败 {arxiv_id}: {e}")
        return (
            PaperAnalysisResponse(
                arxiv_id=arxiv_id,
                title=title,
                analysis={},
                status="error",
                error_message=str(e),
                timings={
                    "pdf_ms": None,
                    "llm_ms": None,
                    "total_ms": None,
                },
            ),
            None,
        )

def normalize_implementation_path(data: dict) -> dict:
    """
    根据 LLM 返回的新格式，构造前端友好的实现路径结构。

    LLM 返回的顶层结构示例：
    {
        "architectural_decision": {...},
        "system_architecture": {...},
        "development_roadmap_detailed": [...],
        "risk_mitigation": {...}
    }
    """
    # 如果已经是前端期望的新结构，直接返回
    if data.get("overview") or data.get("implementation_phases"):
        return data

    architectural_decision = data.get("architectural_decision", {}) or {}
    system_architecture = data.get("system_architecture", {}) or {}
    roadmap = data.get("development_roadmap_detailed", []) or []
    risk_mitigation = data.get("risk_mitigation", {}) or {}

    # 整体概述：优先使用新的 tradeoff_reasoning，其次 reasoning，再加上 pipeline 描述
    overview_parts = []
    if architectural_decision.get("tradeoff_reasoning"):
        overview_parts.append(str(architectural_decision["tradeoff_reasoning"]))
    elif architectural_decision.get("reasoning"):
        overview_parts.append(str(architectural_decision["reasoning"]))

    if system_architecture.get("pipeline_description"):
        overview_parts.append(str(system_architecture["pipeline_description"]))

    overview = "\n\n".join(overview_parts) if overview_parts else None

    # 技术选型：直接暴露当前 LLM 提供的 tech_stack + 选中的 methodology
    tech_stack = system_architecture.get("tech_stack") or []
    integration_strategy = (
        architectural_decision.get("selected_methodology")
        or architectural_decision.get("discarded_methodologies")
        or ""
    )
    technology_selection = (
        {
            "primary_techniques": tech_stack,
            "integration_strategy": integration_strategy,
        }
        if tech_stack or integration_strategy
        else None
    )

    # 实施阶段：从 development_roadmap_detailed 里提取 phase / checklist / definition_of_done
    # 新格式支持：requirement_alignment, user_value, goals, deliverables, checklist, definition_of_done
    implementation_phases = []
    for phase in roadmap:
        if not isinstance(phase, dict):
            continue
        name = phase.get("phase") or phase.get("name") or ""
        checklist = phase.get("checklist") or []
        definition_of_done = phase.get("definition_of_done")
        # 新增字段：需求对齐和用户价值
        requirement_alignment = phase.get("requirement_alignment")
        user_value = phase.get("user_value")
        goals = phase.get("goals") or []
        deliverables = phase.get("deliverables") or []

        # 确保 objectives 和 key_tasks 有区别：
        # - objectives 应该是高层次的目标（goals），如果没有 goals 则从 checklist 中提取关键点
        # - key_tasks 应该是具体的执行任务（checklist）
        # 如果 LLM 只返回了 checklist，我们需要区分使用
        if goals:
            # 有 goals，直接使用
            objectives_list = goals
        elif checklist:
            # 没有 goals，尝试从 checklist 中提取目标性描述（通常 checklist 更具体，我们可以直接使用）
            # 但为了区分，我们可以把 checklist 作为 key_tasks，objectives 留空或使用阶段名称
            objectives_list = [f"完成 {name} 阶段的所有关键任务"]  # 至少给一个占位
        else:
            objectives_list = []

        implementation_phases.append(
            {
                "phase": name,
                "name": name,
                "estimated_time": "",  # 新格式中不再提供具体天数，这里留空占位
                "requirement_alignment": requirement_alignment,  # 该阶段如何服务于用户需求
                "user_value": user_value,  # 该阶段完成后用户能获得什么价值
                "objectives": objectives_list,  # 目标（高层次）
                "deliverables": deliverables if deliverables else ([definition_of_done] if definition_of_done else []),
                "key_tasks": checklist,  # 关键任务（具体执行步骤）
                "definition_of_done": definition_of_done,  # 验收标准
                # 保留原始数据，方便调试和前端使用
                "raw_phase_data": phase,
            }
        )

    # 风险评估：使用 risk_mitigation 的 key 作为风险项，value 作为对应策略
    technical_risks = []
    mitigation_strategies = []
    for key, value in risk_mitigation.items():
        technical_risks.append(str(key))
        if value:
            mitigation_strategies.append(str(value))

    risk_assessment = (
        {
            "technical_risks": technical_risks or None,
            "mitigation_strategies": mitigation_strategies or None,
        }
        if risk_mitigation
        else None
    )

    # 成功标准：从每个阶段的 definition_of_done 收集
    success_criteria = [
        phase.get("definition_of_done")
        for phase in roadmap
        if isinstance(phase, dict) and phase.get("definition_of_done")
    ]

    normalized = {
        "overview": overview,
        "technology_selection": technology_selection,
        "implementation_phases": implementation_phases or None,
        "risk_assessment": risk_assessment,
        "success_criteria": success_criteria or None,
        # 同时把原始结构也暴露给前端，便于展示更详细的信息
        "architectural_decision": architectural_decision or None,
        "system_architecture": system_architecture or None,
        "raw_development_roadmap": roadmap or None,
        "raw_risk_mitigation": risk_mitigation or None,
    }

    # 去掉值为 None 的字段，避免前端多余判断
    return {k: v for k, v in normalized.items() if v}


async def core_generate_implementation_path(
    task_id: str,
    paper_ids: List[str],
    user_requirement: str,
    max_pages_per_paper: int = 20,
    update_progress_callback: Optional[callable] = None,
    user_id: Optional[int] = None,
    history_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    核心业务逻辑：根据多篇论文生成实现路径。

    既可在本地后台任务中调用，也可在 Redis/ARQ worker 中调用。
    """
    overall_start = time.perf_counter()

    if not paper_ids:
        raise ValueError("论文 ID 列表不能为空")

    # 1. 从数据库获取论文信息
    conn = get_db_connection()
    cursor = conn.cursor()

    placeholders = ",".join(["?"] * len(paper_ids))
    query = f"SELECT * FROM papers WHERE arxiv_id IN ({placeholders})"
    cursor.execute(query, paper_ids)
    papers = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if len(papers) != len(paper_ids):
        found_ids = {p["arxiv_id"] for p in papers}
        missing_ids = set(paper_ids) - found_ids
        raise ValueError(f"部分论文未找到: {', '.join(missing_ids)}")

    # 2. 初始化进度
    implementation_progress[task_id] = {
        "status": "running",
        "current_step": "正在解析PDF并进行论文精读",
        "total_papers": len(papers),
        "completed_papers": 0,
        "papers": {
            p["arxiv_id"]: {
                "arxiv_id": p["arxiv_id"],
                "title": p["title"],
                "status": "pending",
                "timings": {
                    "pdf_ms": None,
                    "llm_ms": None,
                    "total_ms": None,
                },
            }
            for p in papers
        },
    }

    if update_progress_callback:
        await update_progress_callback(implementation_progress[task_id])

    pdf_service = get_pdf_service()
    llm_service = get_llm_service()

    papers_analysis: List[PaperAnalysisResponse] = []
    papers_analysis_data: List[dict] = []

    # 为每篇论文创建处理任务
    tasks = [
        process_paper(
            pdf_service=pdf_service,
            llm_service=llm_service,
            paper=paper,
            user_requirement=user_requirement,
            max_pages_per_paper=max_pages_per_paper,
            task_id=task_id,
        )
        for paper in papers
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 检查是否已取消
    if task_id in implementation_progress and implementation_progress[task_id].get("status") == "cancelled":
        logger.info(f"任务 {task_id} 已取消，停止处理论文分析结果")
        return {
            "papers_analysis": [],
            "implementation_path": {},
            "status": "cancelled",
            "error_message": "任务已取消",
        }

    for paper, result in zip(papers, results):
        # 再次检查是否已取消
        if task_id in implementation_progress and implementation_progress[task_id].get("status") == "cancelled":
            logger.info(f"任务 {task_id} 已取消，停止处理论文分析结果")
            break
            
        # 处理 CancelledError
        if isinstance(result, asyncio.CancelledError):
            logger.info(f"论文 {paper.get('arxiv_id')} 处理被取消")
            continue
            
        if isinstance(result, Exception):
            logger.error(f"分析论文失败 {paper.get('arxiv_id')}: {result}")
            papers_analysis.append(
                PaperAnalysisResponse(
                    arxiv_id=paper.get("arxiv_id", ""),
                    title=paper.get("title", ""),
                    analysis={},
                    status="error",
                    error_message=str(result),
                )
            )
            pid = paper.get("arxiv_id")
            if pid and pid in implementation_progress[task_id]["papers"]:
                implementation_progress[task_id]["papers"][pid]["status"] = "error"
            continue

        analysis_resp, summary_data = result
        papers_analysis.append(analysis_resp)
        if summary_data:
            papers_analysis_data.append(summary_data)

        # 更新进度：把已完成的论文分析结果也放到进度中，方便前端实时查看
        implementation_progress[task_id]["completed_papers"] += 1
        # 将已完成的论文分析结果添加到进度中（确保不重复）
        if "papers_analysis" not in implementation_progress[task_id]:
            implementation_progress[task_id]["papers_analysis"] = []
        # 检查是否已存在（避免重复添加）
        existing_ids = {p.get("arxiv_id") for p in implementation_progress[task_id]["papers_analysis"]}
        if analysis_resp.arxiv_id not in existing_ids:
            implementation_progress[task_id]["papers_analysis"].append(analysis_resp.dict())

    # 检查是否已取消
    if task_id in implementation_progress and implementation_progress[task_id].get("status") == "cancelled":
        logger.info(f"任务 {task_id} 已取消，停止后续处理")
        return {
            "papers_analysis": [p.dict() for p in papers_analysis],
            "implementation_path": {},
            "status": "cancelled",
            "error_message": "任务已取消",
        }

    if update_progress_callback:
        await update_progress_callback(implementation_progress[task_id])

    successful_analyses = [p for p in papers_analysis_data if p]
    if not successful_analyses:
        implementation_progress[task_id]["status"] = "error"
        implementation_progress[task_id]["current_step"] = "所有论文分析均失败，无法生成实现路径"
        if update_progress_callback:
            await update_progress_callback(implementation_progress[task_id])
        return {
            "papers_analysis": [p.dict() for p in papers_analysis],
            "implementation_path": {},
            "status": "error",
            "error_message": "所有论文分析均失败，无法生成实现路径",
        }

    # 生成综合实现路径
    try:
        # 检查是否已取消
        if task_id in implementation_progress and implementation_progress[task_id].get("status") == "cancelled":
            logger.info(f"任务 {task_id} 已取消，停止生成实现路径")
            return {
                "papers_analysis": [p.dict() for p in papers_analysis],
                "implementation_path": {},
                "status": "cancelled",
                "error_message": "任务已取消",
            }
            
        implementation_progress[task_id]["current_step"] = "正在生成综合实现路径"
        if update_progress_callback:
            await update_progress_callback(implementation_progress[task_id])

        t_impl_start = time.perf_counter()
        raw_implementation_path = await llm_service.generate_implementation_path(
            papers_analysis=successful_analyses,
            user_requirement=user_requirement,
        )
        t_impl_end = time.perf_counter()
        impl_duration_ms = int((t_impl_end - t_impl_start) * 1000)

        implementation_path = normalize_implementation_path(
            raw_implementation_path if isinstance(raw_implementation_path, dict) else {}
        ) if isinstance(raw_implementation_path, dict) else {}

        overall_end = time.perf_counter()
        total_ms = int((overall_end - overall_start) * 1000)

        # ===== 根据整体方案结果判断成功/失败 =====
        status = "success"
        error_message: Optional[str] = None

        if isinstance(raw_implementation_path, dict) and raw_implementation_path.get("error"):
            # LLM 服务已经明确返回了错误
            status = "error"
            error_message = str(raw_implementation_path.get("error"))
        elif not implementation_path:
            # 归一化之后整体实现路径为空，也视为失败
            status = "error"
            error_message = "实现路径为空或解析失败"

        result: Dict[str, Any] = {
            "papers_analysis": [p.dict() for p in papers_analysis],
            "implementation_path": implementation_path,
            "status": status,
            "timings": {
                "implementation_path_ms": impl_duration_ms,
                "total_ms": total_ms,
                "per_paper": [
                    {
                        "arxiv_id": p.arxiv_id,
                        "title": p.title,
                        "timings": p.timings,
                    }
                    for p in papers_analysis
                ],
            },
        }
        if error_message:
            result["error_message"] = error_message

        # 更新进度中的总体状态
        if status == "success":
            implementation_progress[task_id]["status"] = "finished"
            implementation_progress[task_id]["current_step"] = "实现路径生成完成"
        else:
            implementation_progress[task_id]["status"] = "error"
            implementation_progress[task_id]["current_step"] = "实现路径生成失败"

        # 确保进度中包含完整的论文分析结果和最终结果
        implementation_progress[task_id]["papers_analysis"] = [p.dict() for p in papers_analysis]
        implementation_progress[task_id]["result"] = result

        if update_progress_callback:
            await update_progress_callback(implementation_progress[task_id])

        # 保存实现路径历史到数据库（无论成功/失败都记录，但区分 status）
        if user_id is not None:
            try:
                save_implementation_path_history(
                    user_id=user_id,
                    history_id=history_id,
                    paper_ids=paper_ids,
                    user_requirement=user_requirement,
                    implementation_path=result.get("implementation_path", {}),
                    papers_analysis=result["papers_analysis"],
                    timings=result.get("timings"),
                    status=status,
                    error_message=error_message,
                )
            except Exception as e:
                logger.error(f"保存实现路径历史失败: {e}")

        return result

    except Exception as e:
        logger.error(f"生成实现路径失败: {e}")
        implementation_progress[task_id]["status"] = "error"
        implementation_progress[task_id]["current_step"] = "生成实现路径失败"
        if update_progress_callback:
            await update_progress_callback(implementation_progress[task_id])
        return {
            "papers_analysis": [p.dict() for p in papers_analysis],
            "implementation_path": {},
            "status": "error",
            "error_message": f"生成实现路径失败: {str(e)}",
        }


@router.post("/generate-implementation-path")
async def generate_implementation_path(
    request: Request,
    body: GeneratePathRequest,
    current_user: str = Depends(get_current_user),
):
    """
    混合模式生成实现路径：
    - 若检测到 Redis，可将任务投递到 ARQ 队列（异步执行）
    - 若未检测到 Redis，则在当前进程内起本地后台任务

    无论哪种模式，进度都可通过 /implementation-progress/{task_id} 查询。
    """
    try:
        task_id = body.task_id or str(int(time.time() * 1000))

        if not body.paper_ids:
            raise HTTPException(status_code=400, detail="论文ID列表不能为空")

        if len(body.paper_ids) > 5:
            raise HTTPException(status_code=400, detail="最多选择5篇论文进行分析")

        # 获取用户需求：优先从history_id获取，否则使用直接提供的需求
        user_requirement: Optional[str] = None

        if body.history_id:
            user = get_user_by_username(current_user)
            user_id = user["id"] if user else None

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT search_desc FROM match_history WHERE id = ? AND user_id = ?",
                (body.history_id, user_id),
            )
            history = cursor.fetchone()
            conn.close()

            if history:
                user_requirement = history["search_desc"]
            else:
                raise HTTPException(
                    status_code=404, detail="匹配历史不存在或无权限访问"
                )

        if not user_requirement:
            user_requirement = body.user_requirement

        if not user_requirement or not user_requirement.strip():
            raise HTTPException(
                status_code=400,
                detail="用户需求不能为空，请提供user_requirement或history_id",
            )

        max_pages = body.max_pages_per_paper or 20

        # 场景 A：Redis 可用 -> 扔给 ARQ 队列
        if getattr(request.app.state, "use_redis", False):
            user = get_user_by_username(current_user)
            user_id = user["id"] if user else None
            
            redis_pool = request.app.state.redis_pool
            # enqueue_job 返回 job 对象
            await redis_pool.enqueue_job(
                "task_wrapper_generate_path",  # worker.py 里的函数名
                task_id,
                body.paper_ids,
                user_requirement,
                max_pages,
                user_id,  # 传递 user_id
                body.history_id,  # 传递 history_id
                _job_id=task_id,  # 强制使用前端传来的 task_id 作为 Job ID
            )
            return {"status": "queued", "task_id": task_id, "mode": "redis"}

        # 场景 B：Redis 不可用 -> 本地后台任务（asyncio.create_task）
        user = get_user_by_username(current_user)
        user_id = user["id"] if user else None

        async def update_local_progress(state: Dict[str, Any]):
            implementation_progress[task_id] = state

        async def _run_local_task():
            await core_generate_implementation_path(
                task_id=task_id,
                paper_ids=body.paper_ids,
                user_requirement=user_requirement or "",
                max_pages_per_paper=max_pages,
                update_progress_callback=update_local_progress,
                user_id=user_id,
                history_id=body.history_id,
            )

        asyncio.create_task(_run_local_task())

        return {"status": "processing", "task_id": task_id, "mode": "local"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成实现路径接口失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/implementation-progress/{task_id}")
async def get_implementation_progress(
    request: Request,
    task_id: str,
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    统一查询实现路径生成的实时进度：
    - 优先从本地内存 implementation_progress 中读取
    - 若未命中且 Redis 已启用，则从 Redis 中读取 worker 写入的进度
    
    返回的进度中包含：
    - status: 任务状态（running/finished/error）
    - current_step: 当前步骤描述
    - total_papers: 总论文数
    - completed_papers: 已完成论文数
    - papers: 每篇论文的进度状态
    - papers_analysis: 已完成的论文分析结果列表（逐步更新）
    - result: 最终结果（任务完成时包含完整的 implementation_path 和 papers_analysis）
    """
    # 1. 先查本地内存
    progress = implementation_progress.get(task_id)
    if progress:
        # 确保返回的进度包含 papers_analysis（如果存在）
        return progress

    # 2. 如果本地没有，且 Redis 可用，则查 Redis
    if getattr(request.app.state, "use_redis", False):
        try:
            redis = request.app.state.redis_pool
            raw_progress = await redis.get(f"progress:{task_id}")
            if raw_progress:
                import json

                progress_data = json.loads(raw_progress)
                # 确保返回的进度包含 papers_analysis（如果存在）
                return progress_data
        except Exception as e:
            logger.error(f"从 Redis 获取实现路径进度失败: {e}")

    # 3. 兜底
    return {
        "status": "unknown",
        "current_step": "未找到该任务",
        "total_papers": 0,
        "completed_papers": 0,
        "papers": {},
        "papers_analysis": [],
    }


@router.post("/cancel-implementation-path/{task_id}")
async def cancel_implementation_path(
    request: Request,
    task_id: str,
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    取消正在生成的实现路径任务
    """
    try:
        # 1. 检查本地内存中的任务
        if task_id in implementation_progress:
            progress = implementation_progress[task_id]
            if progress.get("status") == "running":
                # 标记任务为已取消
                implementation_progress[task_id] = {
                    **progress,
                    "status": "cancelled",
                    "current_step": "任务已取消",
                }
                logger.info(f"任务 {task_id} 已标记为取消（本地模式）")
                return {"status": "cancelled", "message": "任务已取消"}
            else:
                return {"status": "error", "message": f"任务状态为 {progress.get('status')}，无法取消"}

        # 2. 如果 Redis 可用，尝试取消 Redis 中的任务
        if getattr(request.app.state, "use_redis", False):
            try:
                redis = request.app.state.redis_pool
                # 尝试取消 ARQ 任务
                job = await redis.get_job(task_id)
                if job:
                    await job.abort()
                    logger.info(f"任务 {task_id} 已取消（Redis 模式）")
                    return {"status": "cancelled", "message": "任务已取消"}
                else:
                    return {"status": "error", "message": "未找到该任务"}
            except Exception as e:
                logger.error(f"取消 Redis 任务失败: {e}")
                return {"status": "error", "message": f"取消任务失败: {str(e)}"}

        return {"status": "error", "message": "未找到该任务"}
    except Exception as e:
        logger.error(f"取消实现路径任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.get("/implementation-path-history/{history_id}")
async def get_implementation_path_history(
    history_id: int,
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    获取指定匹配历史（话题）下所有生成过的实现路径方案
    
    返回该话题下所有历史方案的列表，按创建时间倒序排列。
    """
    try:
        user = get_user_by_username(current_user)
        user_id = user["id"] if user else None
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="用户信息无效")
        
        # 验证 history_id 是否属于当前用户
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM match_history WHERE id = ? AND user_id = ?",
            (history_id, user_id),
        )
        history = cursor.fetchone()
        conn.close()
        
        if not history:
            raise HTTPException(
                status_code=404, detail="匹配历史不存在或无权限访问"
            )
        
        # 获取该话题下的所有实现路径历史
        history_list = get_implementation_path_history_by_history_id(
            user_id=user_id,
            history_id=history_id,
        )
        
        return {
            "history_id": history_id,
            "total": len(history_list),
            "items": history_list,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实现路径历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/implementation-path-history")
async def get_all_implementation_path_history_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    获取当前用户的所有实现路径历史方案（不限制话题）
    
    支持分页查询，按创建时间倒序排列。
    """
    try:
        user = get_user_by_username(current_user)
        user_id = user["id"] if user else None
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="用户信息无效")
        
        result = get_all_implementation_path_history(
            user_id=user_id,
            page=page,
            page_size=page_size,
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取所有实现路径历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
