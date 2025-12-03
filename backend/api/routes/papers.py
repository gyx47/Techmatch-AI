"""
论文相关路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Tuple, Dict, Any
import pydantic as pydantic
import requests
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
import time
from database.database import save_paper, get_papers_by_query, get_db_connection, get_user_by_username
from api.routes.auth import get_current_user
from services.pdf import get_pdf_service
from services.llm_service import get_llm_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# =======================
# 全局实现路径进度状态
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

@router.get("/local-search", response_model=List[PaperResponse])
async def local_search_papers(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, description="结果数量限制"),
    current_user: str = Depends(get_current_user)
):
    """本地数据库搜索论文"""
    try:
        papers = get_papers_by_query(query, limit)
        return papers
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
        logger.info(f"开始分析论文: {title} ({arxiv_id})")

        # ==============================
        # 1. 下载 / 解析 PDF（在线程池中）
        # ==============================
        t_pdf_start = time.perf_counter()
        pdf_content = await asyncio.to_thread(
            pdf_service.get_paper_content,
            pdf_url,
            arxiv_id,
            max_pages=max_pages_per_paper,
        )
        t_pdf_end = time.perf_counter()
        pdf_duration_ms = int((t_pdf_end - t_pdf_start) * 1000)

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

        # ==============================
        # 2. LLM 精读分析
        # ==============================
        t_llm_start = time.perf_counter()
        analysis = await llm_service.analyze_paper_with_router(
            paper_title=title,
            paper_abstract=abstract,
            pdf_content=pdf_content,
            user_requirement=user_requirement,
        )
        t_llm_end = time.perf_counter()
        llm_duration_ms = int((t_llm_end - t_llm_start) * 1000)

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

@router.post("/generate-implementation-path", response_model=ImplementationPathResponse)
async def generate_implementation_path(
    request: GeneratePathRequest,
    current_user: str = Depends(get_current_user)
):
    """
    基于选中的论文生成实现路径
    
    流程：
    1. 获取用户需求（从history_id或直接提供）
    2. 根据arxiv_id从数据库获取论文信息
    3. 下载并解析每篇论文的PDF
    4. 使用AI对PDF进行精读分析
    5. 综合多篇论文的分析结果，生成实现路径
    """
    try:
        overall_start = time.perf_counter()
        task_id = request.task_id

        if not request.paper_ids:
            raise HTTPException(status_code=400, detail="论文ID列表不能为空")
        
        # 获取用户需求：优先从history_id获取，否则使用直接提供的需求
        user_requirement = None
        
        if request.history_id:
            # 从匹配历史获取需求
            user = get_user_by_username(current_user)
            user_id = user["id"] if user else None
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT search_desc FROM match_history WHERE id = ? AND user_id = ?",
                (request.history_id, user_id)
            )
            history = cursor.fetchone()
            conn.close()
            
            if history:
                user_requirement = history["search_desc"]
            else:
                raise HTTPException(status_code=404, detail="匹配历史不存在或无权限访问")
        
        if not user_requirement:
            user_requirement = request.user_requirement
        
        if not user_requirement or not user_requirement.strip():
            raise HTTPException(status_code=400, detail="用户需求不能为空，请提供user_requirement或history_id")
        
        if len(request.paper_ids) > 5:
            raise HTTPException(status_code=400, detail="最多选择5篇论文进行分析")

        pdf_service = get_pdf_service()
        llm_service = get_llm_service()
        
        # 从数据库获取论文信息
        conn = get_db_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join(['?'] * len(request.paper_ids))
        query = f"SELECT * FROM papers WHERE arxiv_id IN ({placeholders})"
        cursor.execute(query, request.paper_ids)
        papers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        if len(papers) != len(request.paper_ids):
            found_ids = {p['arxiv_id'] for p in papers}
            missing_ids = set(request.paper_ids) - found_ids
            raise HTTPException(
                status_code=404, 
                detail=f"部分论文未找到: {', '.join(missing_ids)}"
            )

        # 初始化进度结构
        if task_id:
            implementation_progress[task_id] = {
                "status": "running",
                "current_step": "正在解析PDF并进行论文精读",
                "total_papers": len(papers),
                "completed_papers": 0,
                "papers": {
                    p["arxiv_id"]: {
                        "arxiv_id": p["arxiv_id"],
                        "title": p["title"],
                        "status": "pending",  # pending / pdf_done / pdf_failed / done / error
                        "timings": {
                            "pdf_ms": None,
                            "llm_ms": None,
                            "total_ms": None,
                        },
                    }
                    for p in papers
                },
            }
        
        # 对每篇论文进行 PDF 精读分析（并发执行）
        papers_analysis: List[PaperAnalysisResponse] = []
        papers_analysis_data: List[dict] = []  # 用于生成实现路径

        max_pages_per_paper = request.max_pages_per_paper or 20

        # 为每篇论文创建一个处理任务
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

        for paper, result in zip(papers, results):
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
                continue

            analysis_resp, summary_data = result
            papers_analysis.append(analysis_resp)
            if summary_data:
                papers_analysis_data.append(summary_data)

            # 单篇完成后，更新整体 completed_papers
            if task_id and task_id in implementation_progress:
                implementation_progress[task_id]["completed_papers"] += 1

        # 如果至少有一篇论文分析成功，生成实现路径
        successful_analyses = [p for p in papers_analysis_data if p]
        
        if not successful_analyses:
            return ImplementationPathResponse(
                papers_analysis=papers_analysis,
                implementation_path={},
                status="error",
                error_message="所有论文分析均失败，无法生成实现路径"
            )
        
        # 生成综合实现路径
        try:
            if task_id and task_id in implementation_progress:
                implementation_progress[task_id]["current_step"] = "正在生成综合实现路径"

            t_impl_start = time.perf_counter()
            raw_implementation_path = await llm_service.generate_implementation_path(
                papers_analysis=successful_analyses,
                user_requirement=request.user_requirement
            )
            t_impl_end = time.perf_counter()
            impl_duration_ms = int((t_impl_end - t_impl_start) * 1000)

            if "error" in raw_implementation_path:
                resp = ImplementationPathResponse(
                    papers_analysis=papers_analysis,
                    implementation_path={},
                    status="error",
                    error_message=raw_implementation_path.get("error", "生成实现路径失败"),
                    timings={
                        "implementation_path_ms": impl_duration_ms,
                        "total_ms": int((time.perf_counter() - overall_start) * 1000),
                        "per_paper": [
                            {
                                "arxiv_id": p.arxiv_id,
                                "title": p.title,
                                "timings": p.timings,
                            }
                            for p in papers_analysis
                        ],
                    },
                )
                if task_id and task_id in implementation_progress:
                    implementation_progress[task_id]["status"] = "error"
                    implementation_progress[task_id]["current_step"] = "生成实现路径失败"
                return resp

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
                technology_selection = {
                    "primary_techniques": tech_stack,
                    "integration_strategy": integration_strategy,
                } if tech_stack or integration_strategy else None

                # 实施阶段：从 development_roadmap_detailed 里提取 phase / checklist / definition_of_done
                implementation_phases = []
                for phase in roadmap:
                    if not isinstance(phase, dict):
                        continue
                    name = phase.get("phase") or phase.get("name") or ""
                    checklist = phase.get("checklist") or []
                    definition_of_done = phase.get("definition_of_done")

                    implementation_phases.append({
                        "phase": name,
                        "name": name,
                        "estimated_time": "",  # 新格式中不再提供具体天数，这里留空占位
                        "objectives": checklist,
                        "deliverables": [definition_of_done] if definition_of_done else [],
                        "key_tasks": checklist,
                    })

                # 风险评估：使用 risk_mitigation 的 key 作为风险项，value 作为对应策略
                technical_risks = []
                mitigation_strategies = []
                for key, value in risk_mitigation.items():
                    technical_risks.append(str(key))
                    if value:
                        mitigation_strategies.append(str(value))

                risk_assessment = {
                    "technical_risks": technical_risks or None,
                    "mitigation_strategies": mitigation_strategies or None,
                } if risk_mitigation else None

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

            implementation_path = normalize_implementation_path(raw_implementation_path)

            overall_end = time.perf_counter()
            total_ms = int((overall_end - overall_start) * 1000)

            logger.info(
                f"实现路径生成完成：LLM 汇总耗时 {impl_duration_ms} ms，总接口耗时 {total_ms} ms"
            )

            resp = ImplementationPathResponse(
                papers_analysis=papers_analysis,
                implementation_path=implementation_path,
                status="success",
                timings={
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
            )

            if task_id and task_id in implementation_progress:
                implementation_progress[task_id]["status"] = "finished"
                implementation_progress[task_id]["current_step"] = "实现路径生成完成"

            return resp
            
        except Exception as e:
            logger.error(f"生成实现路径失败: {e}")
            if task_id and task_id in implementation_progress:
                implementation_progress[task_id]["status"] = "error"
                implementation_progress[task_id]["current_step"] = "生成实现路径失败"
            return ImplementationPathResponse(
                papers_analysis=papers_analysis,
                implementation_path={},
                status="error",
                error_message=f"生成实现路径失败: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成实现路径接口失败: {e}")
        if request.task_id and request.task_id in implementation_progress:
            implementation_progress[request.task_id]["status"] = "error"
            implementation_progress[request.task_id]["current_step"] = "接口执行失败"
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/implementation-progress/{task_id}")
async def get_implementation_progress(
    task_id: str,
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    查询实现路径生成的实时进度
    由前端在调用 /generate-implementation-path 时传入的 task_id 标识
    """
    progress = implementation_progress.get(task_id)
    if not progress:
        return {
            "status": "unknown",
            "current_step": "未找到该任务",
            "total_papers": 0,
            "completed_papers": 0,
            "papers": {},
        }
    return progress
