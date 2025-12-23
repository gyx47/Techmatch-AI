"""
后端API接口 - 需求详情和匹配理由生成
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import logging

from api.routes.auth import get_current_user_optional as get_current_user
from services.llm_service import get_llm_service
from database.database import get_requirements_by_query_paginated, get_db_connection


router = APIRouter()
logger = logging.getLogger(__name__)

class GenerateAnalysisRequest(BaseModel):
    requirement_data: Dict[str, Any]
    user_input: Optional[str] = ""
    paper_title: Optional[str] = ""
    paper_abstract: Optional[str] = ""
    analysis_type: str = "requirement_analysis"

class GenerateAnalysisResponse(BaseModel):
    success: bool
    reason: str
    implementation_suggestion: str
    score: Optional[int] = 0
    match_type: Optional[str] = ""

class DetailedReportRequest(BaseModel):
    requirement_data: Dict[str, Any]
    user_input: Optional[str] = ""
    report_type: str = "detailed_cooperation"

class DetailedReportResponse(BaseModel):
    success: bool
    report: Dict[str, Any]
    message: str = ""


@router.post("/generate-analysis", response_model=GenerateAnalysisResponse)
async def generate_requirement_analysis(
    request: GenerateAnalysisRequest,
    current_user: str = Depends(get_current_user)
):
    """
    生成需求分析报告
    根据用户输入（搜索文本或论文信息）对需求进行智能分析
    """
    try:
        llm_service = get_llm_service()
        requirement = request.requirement_data
        
        # 构建智能提示词
        prompt = build_analysis_prompt(
            requirement=requirement,
            user_input=request.user_input,
            paper_title=request.paper_title,
            paper_abstract=request.paper_abstract,
            analysis_type=request.analysis_type
        )
        
        try:
            # 调用DeepSeek进行智能分析
            content = await llm_service._call_deepseek([
                {
                    "role": "system", 
                    "content": "你是一位资深的企业技术顾问和技术转移专家。请用中文回答，分析要专业、详细、有针对性。"
                },
                {"role": "user", "content": prompt}
            ])
            
            # 解析LLM返回的JSON
            result = json.loads(content)
            
            return GenerateAnalysisResponse(
                success=True,
                reason=result.get("reason", "未生成分析理由"),
                implementation_suggestion=result.get("implementation_suggestion", "暂无实施建议"),
                score=result.get("score", 70),
                match_type=result.get("match_type", "B级-需技术适配")
            )
            
        except Exception as llm_error:
            logger.error(f"LLM分析失败: {llm_error}")
            # LLM调用失败时，返回基于规则的分析
            return generate_fallback_analysis(requirement, request.user_input)
            
    except Exception as e:
        logger.error(f"生成需求分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成需求分析失败: {str(e)}")

def build_analysis_prompt(requirement, user_input="", paper_title="", paper_abstract="", analysis_type="requirement_analysis"):
    """
    根据不同的分析类型构建智能提示词
    """
    
    # 提取需求关键信息
    title = requirement.get('title', '未命名需求')
    industry = requirement.get('industry', '未指定行业')
    technical_level = requirement.get('technical_level', '中等')
    market_size = requirement.get('market_size', '中型')
    pain_points = requirement.get('pain_points', '暂无痛点描述')[:500]
    description = requirement.get('description', '暂无详细描述')[:1000]
    
    if analysis_type == "paper_matching" and paper_title:
        # 论文匹配分析
        return f"""
作为技术转移专家，请分析以下科研成果与企业需求的匹配程度。

【科研成果信息】
论文标题：{paper_title}
论文摘要：{paper_abstract[:800] if paper_abstract else '暂无详细摘要'}

【企业需求详情】
需求标题：{title}
所属行业：{industry}
技术难度：{technical_level}
市场规模：{market_size}
核心痛点：{pain_points}
详细描述：{description}

请从以下维度进行详细分析：
1. 技术契合度（40%权重）：论文方法如何解决需求痛点
2. 商业价值（30%权重）：市场机会和收益预期
3. 实施可行性（30%权重）：技术落地的难易程度

输出要求：
请返回JSON格式，包含以下字段：
{{
    "reason": "详细的匹配分析（不少于300字）",
    "implementation_suggestion": "具体的实施建议（不少于200字）",
    "score": "匹配分数（0-100的整数）",
    "match_type": "匹配等级（S/A/B/C级-描述）"
}}

注意：评分要合理，不要给极端分数。匹配类型示例：S级-完美适配、A级-技术相关、B级-潜在可用、C级-参考。
"""
    
    elif user_input:
        # 基于用户搜索文本的需求分析
        return f"""
作为企业需求分析师，请根据用户关注点分析以下企业需求。

【用户关注点】
{user_input}

【企业需求详情】
需求标题：{title}
所属行业：{industry}
技术难度：{technical_level}
市场规模：{market_size}
核心痛点：{pain_points}
详细描述：{description}

请从以下角度进行分析：
1. 需求与用户关注的匹配度
2. 技术可行性和实施难度
3. 市场前景和商业价值
4. 风险分析和应对策略

输出要求：
请返回JSON格式，包含以下字段：
{{
    "reason": "详细的分析报告（不少于400字）",
    "implementation_suggestion": "分阶段的实施建议（不少于250字）",
    "score": "需求价值评分（0-100的整数）",
    "match_type": "需求等级（S/A/B/C级-描述）"
}}

注意：评分要客观，分析要具体。
"""
    
    else:
        # 需求自身分析
        return f"""
作为需求评估专家，请对以下企业需求进行全面评估。

【需求详情】
标题：{title}
行业：{industry}
技术难度：{technical_level}
市场规模：{market_size}
核心痛点：{pain_points}
详细描述：{description}

评估维度：
1. 市场需求和规模（25%）
2. 技术成熟度和可行性（25%）
3. 实施难度和成本（20%）
4. 竞争优势和差异化（15%）
5. 风险控制和合规性（15%）

输出要求：
请返回JSON格式，包含以下字段：
{{
    "reason": "全面的需求评估报告（不少于500字）",
    "implementation_suggestion": "详细的实施路径规划（不少于300字）",
    "score": "综合评分（0-100的整数）",
    "match_type": "需求等级（S/A/B/C级-描述）"
}}
"""

def generate_fallback_analysis(requirement, user_input=""):
    """
    LLM失败时的备用分析生成
    """
    industry = requirement.get('industry', '相关')
    technical_level = requirement.get('technical_level', '中等')
    market_size = requirement.get('market_size', '中型')
    
    # 根据需求信息生成基本分析
    reason = f"""
该需求在{industry}行业具有较好的应用前景。

技术可行性分析：
- 技术难度为{technical_level}，在当前技术水平下具备实施条件
- 需求痛点明确，解决方案方向清晰
- 在{market_size}规模市场中有明确的商业价值

{"用户关注点与需求高度相关，建议重点考虑。" if user_input else ""}

建议进行详细的技术验证和市场调研。
"""
    
    implementation_suggestion = f"""
实施建议（分三阶段）：
第一阶段（1-2个月）：需求细化与技术验证
  1. 详细需求分析和方案设计
  2. 技术可行性验证和原型开发
  3. 初步的成本和资源评估

第二阶段（2-4个月）：方案完善与测试
  1. 系统架构设计和详细开发计划
  2. 核心功能开发和测试
  3. 用户反馈收集和优化

第三阶段（3-6个月）：部署与推广
  1. 系统部署和上线运行
  2. 用户培训和文档编写
  3. 运营维护和持续优化
"""
    
    # 基于需求信息估算分数
    score = 70  # 默认70分
    
    if technical_level == "高":
        score -= 10
    elif technical_level == "低":
        score += 10
    
    if market_size == "大型":
        score += 15
    elif market_size == "小型":
        score -= 5
    
    # 确保分数在合理范围
    score = max(30, min(95, score))
    
    # 确定匹配类型
    if score >= 85:
        match_type = "A级-技术相关"
    elif score >= 70:
        match_type = "B级-潜在可用"
    elif score >= 50:
        match_type = "C级-参考"
    else:
        match_type = "需进一步评估"
    
    return GenerateAnalysisResponse(
        success=False,
        reason=reason,
        implementation_suggestion=implementation_suggestion,
        score=score,
        match_type=match_type
    )


@router.get("/matching/requirements/{requirement_id}")
async def get_requirement_detail(requirement_id: str):
    """
    获取需求详情
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                r.*,
                u.username as contact_name,
                u.email as contact_email
            FROM requirements r
            LEFT JOIN users u ON r.contact_info = u.email
            WHERE r.requirement_id = ? AND r.status = 'active'
        """, (requirement_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="需求不存在或已被删除")
        
        requirement = dict(row)
        return requirement
        
    except Exception as e:
        logger.error(f"获取需求详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取需求详情失败")

@router.post("/matching/generate-reason")
async def generate_matching_reason(data: Dict[str, Any]):
    """
    生成匹配理由和实施建议
    """
    try:
        llm_service = get_llm_service()
        
        paper_title = data.get("paper_title", "")
        paper_abstract = data.get("paper_abstract", "")
        requirement_title = data.get("requirement_title", "")
        requirement_description = data.get("requirement_description", "")
        requirement_id = data.get("requirement_id", "")
        
        # 调用LLM生成详细的匹配理由
        prompt = f"""
        作为技术转移专家，请分析以下科研成果与需求的匹配度，并提供详细的推荐理由和实施建议。

        科研成果：
        标题：{paper_title}
        摘要：{paper_abstract}

        企业需求：
        标题：{requirement_title}
        描述：{requirement_description}

        请从以下维度进行分析：
        1. 技术契合度：论文方法如何解决需求的痛点
        2. 实施可行性：技术落地的难易程度和成本
        3. 商业价值：该匹配带来的潜在收益
        4. 风险分析：可能面临的技术和市场风险

        返回JSON格式：
        {{
            "reason": "详细的匹配理由，不少于200字",
            "implementation_suggestion": "具体的实施建议，不少于150字",
            "estimated_time": "预计实施时间",
            "success_probability": "成功概率估算（0-100%）"
        }}
        """
        
        try:
            # 调用LLM服务
            content = await llm_service._call_deepseek([
                {"role": "user", "content": prompt}
            ])
            
            import json
            result = json.loads(content)
            
            # 保存匹配理由到数据库
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO match_reasons 
                (paper_title, requirement_id, reason, suggestion, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                paper_title,
                requirement_id,
                result.get("reason", ""),
                result.get("implementation_suggestion", "")
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "reason": result.get("reason", ""),
                "implementation_suggestion": result.get("implementation_suggestion", ""),
                "estimated_time": result.get("estimated_time", "3-6个月"),
                "success_probability": result.get("success_probability", "70%")
            }
            
        except Exception as e:
            logger.error(f"LLM生成匹配理由失败: {e}")
            
            # 如果LLM失败，返回默认理由
            default_reason = f"科研成果《{paper_title}》与企业需求《{requirement_title}》高度相关。该技术能够有效解决需求中的核心痛点，在{data.get('industry', '相关行业')}具有广阔的应用前景。"
            
            default_suggestion = f"建议分阶段实施：1. 技术验证阶段（1-2个月）；2. 原型开发阶段（2-3个月）；3. 试点应用阶段（3-6个月）；4. 规模化推广阶段。"
            
            return {
                "success": False,
                "reason": default_reason,
                "implementation_suggestion": default_suggestion,
                "estimated_time": "6-12个月",
                "success_probability": "65%"
            }
            
    except Exception as e:
        logger.error(f"生成匹配理由失败: {e}")
        raise HTTPException(status_code=500, detail="生成匹配理由失败")

@router.get("/papers/{paper_id}")
async def get_paper_detail(paper_id: str):
    """
    获取论文详情
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM papers 
            WHERE arxiv_id = ? OR id = ?
        """, (paper_id, paper_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            # 尝试从向量库或其他地方获取
            vector_service = get_vector_service()
            paper_data = vector_service.get_paper_by_id(paper_id)
            if paper_data:
                return paper_data
            raise HTTPException(status_code=404, detail="论文不存在")
        
        return dict(row)
        
    except Exception as e:
        logger.error(f"获取论文详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取论文详情失败")

@router.get("/list")
async def get_requirements_list(
    query: str = Query("", description="搜索关键词（可选）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: str = Depends(get_current_user)
):
    """获取系统生成的需求列表（分页、搜索）"""
    try:
        result = get_requirements_by_query_paginated(query, page, page_size)
        return result
    except Exception as e:
        logger.error(f"获取需求列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取需求列表失败: {str(e)}")
    

@router.post("/generate-detailed-report", response_model=DetailedReportResponse)
async def generate_detailed_cooperation_report(
    request: DetailedReportRequest,
    current_user: str = Depends(get_current_user)
):
    """
    生成详细合作报告
    """
    try:
        llm_service = get_llm_service()
        requirement = request.requirement_data
        
        # 构建详细的报告生成提示词
        prompt = build_detailed_report_prompt(requirement, request.user_input)
        
        content = await llm_service._call_deepseek([
            {"role": "system", "content": "你是一位资深的企业合作顾问和技术转移专家。"},
            {"role": "user", "content": prompt}
        ], temperature=0.7, max_tokens=3000)
        
        result = json.loads(content)
        
        return DetailedReportResponse(
            success=True,
            report=result,
            message="详细合作报告生成成功"
        )
        
    except Exception as e:
        logger.error(f"生成详细合作报告失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成详细合作报告失败: {str(e)}")

def build_detailed_report_prompt(requirement, user_input=""):
    """构建详细报告提示词（兼容系统生成需求和用户发布需求）"""
    
    # 兼容不同来源的需求字段
    # 系统生成需求(requirements)字段：technical_level, market_size, pain_points, contact_info
    # 用户发布需求(published_needs)字段：urgency_level, budget_range, cooperation_preference, company_name, contact_name, contact_phone, contact_email
    
    technical_level = requirement.get('technical_level', '') or requirement.get('urgency_level', '')
    market_size = requirement.get('market_size', '') or requirement.get('budget_range', '')
    pain_points = requirement.get('pain_points', '')
    company_info = requirement.get('company_name', '') or (requirement.get('contact_info', '') and requirement.get('contact_info', '').split('@')[0] if '@' in str(requirement.get('contact_info', '')) else '')
    
    prompt = f"""
作为资深的企业合作顾问，请为以下需求生成一份详细的企业合作分析报告。

【需求基本信息】
标题：{requirement.get('title', '')}
行业：{requirement.get('industry', '')}
技术难度/紧急程度：{technical_level}
市场规模/预算范围：{market_size}
核心痛点：{str(pain_points)[:500] if pain_points else '未提供'}
详细描述：{requirement.get('description', '')[:1000]}
公司信息：{company_info}

【已有的匹配信息】
匹配分数：{requirement.get('match_score', '未评分')}
匹配等级：{requirement.get('match_type', '未分类')}
匹配理由：{requirement.get('match_reason', '无')}

【用户关注点】
{user_input if user_input else '无特定关注点'}

【报告要求】
请生成一份专业、详细的合作分析报告，包含以下部分：

1. 项目概述：包括合作潜力评分、建议合作类型
2. 详细需求分析：深入分析技术需求、业务需求，列出技术需求要点
3. 痛点深度剖析：对每个痛点进行详细分析，包括严重程度、影响范围
4. AI推荐理由：从技术匹配度、商业价值、实施可行性三个维度评分并详细分析
5. 合作建议：提供具体的合作建议，包括建议内容、优先级、预计耗时、所需资源、预期成果
6. 合作周期规划：分阶段规划合作周期，包括各阶段的名称、持续时间、预算、关键任务、预期成果
7. 风险分析与应对：分析合作可能面临的风险，包括风险类型、等级、发生概率、描述、应对措施
8. 财务分析（可选）：包括总投资预算、预计ROI、回本周期、成功概率、备注
9. 下一步行动：提供具体的下一步行动建议

【输出格式】
请返回JSON格式，数据结构示例如下：
{{
    "overall_score": 85,
    "cooperation_type": "技术开发与咨询",
    "detailed_analysis": "详细的...",
    "technical_points": ["要点1", "要点2"],
    "pain_points_detail": [
        {{
            "title": "痛点标题",
            "severity": "高/中/低",
            "description": "详细描述",
            "impact": "影响范围"
        }}
    ],
    "technical_score": 85,
    "business_score": 80,
    "implementation_score": 75,
    "recommendation_analysis": "详细的分析...",
    "cooperation_suggestions": [
        {{
            "title": "建议标题",
            "content": "建议内容",
            "priority": "高/中/低",
            "estimated_time": "预计耗时",
            "resource_requirements": "所需资源",
            "expected_outcomes": "预期成果"
        }}
    ],
    "cooperation_phases": [
        {{
            "name": "阶段名称",
            "duration": "持续时间",
            "budget": "预算",
            "key_tasks": ["任务1", "任务2"],
            "expected_outcomes": "预期成果"
        }}
    ],
    "risk_analysis": [
        {{
            "type": "风险类型",
            "level": "高/中/低",
            "probability": "发生概率",
            "description": "风险描述",
            "mitigation_strategy": "应对措施"
        }}
    ],
    "financial_analysis": {{
        "total_budget": "总投资预算",
        "roi_estimate": "预计ROI",
        "payback_period": "回本周期",
        "success_probability": "成功概率",
        "note": "备注"
    }},
    "next_steps": [
        {{
            "title": "行动标题",
            "description": "行动描述",
            "suggested_time": "建议时间",
            "resource_needed": "所需资源"
        }}
    ]
}}

注意：所有内容必须详尽、具体、专业，用中文回答。分析要深入，建议要可执行。
"""
    
    return prompt
    