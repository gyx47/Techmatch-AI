"""
LLM 服务 - 使用 LangChain/LangGraph 优化版本
这是一个示例实现，展示如何将 HTTP 请求包装在 LangChain 工作流中
"""
import logging
import os
from typing import Dict, List
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import BaseOutputParser
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
import json

logger = logging.getLogger(__name__)

# ==================== 使用 LangChain 的优势 ====================
# 1. 统一的 LLM 接口抽象
# 2. 内置的重试、超时、流式输出
# 3. 链式调用（Chains）和工作流编排
# 4. 输出解析（Output Parsing）
# 5. 可观测性（Observability）和调试工具
# 6. 成本追踪（Token 计数）

class QueryExpansionOutput(BaseOutputParser):
    """查询扩展输出解析器"""
    def parse(self, text: str) -> str:
        # 提取关键词和摘要
        if "[Abstract]:" in text:
            return text
        # 如果没有找到，尝试提取 JSON
        try:
            data = json.loads(text)
            keywords = ", ".join(data.get("keywords", []))
            abstract = data.get("abstract", "")
            return f"{keywords}. [Abstract]: {abstract}"
        except:
            return text

class PaperScoreOutput(BaseOutputParser):
    """论文评分输出解析器"""
    def parse(self, text: str) -> Dict:
        try:
            data = json.loads(text)
            return {
                "score": int(data.get("score", 0)),
                "reason": data.get("reason", "")
            }
        except Exception as e:
            logger.error(f"解析评分输出失败: {e}")
            return {"score": 0, "reason": "解析失败"}

class LLMServiceLangChain:
    """
    使用 LangChain 优化的 LLM 服务
    
    优势：
    1. 统一的接口抽象，支持多种 LLM（OpenAI, DeepSeek, 本地模型等）
    2. 内置重试机制、超时控制
    3. 链式调用，代码更清晰
    4. 输出解析，自动处理 JSON
    5. 可观测性，追踪 token 使用
    """
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        # 使用 LangChain 的 ChatOpenAI，但配置为 DeepSeek API
        # 注意：DeepSeek 兼容 OpenAI API 格式
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            temperature=0.7,
            openai_api_key=self.api_key,
            openai_api_base="https://api.deepseek.com/v1",
            max_tokens=500,
            timeout=600.0,
            max_retries=3,  # 自动重试 3 次
        )
        
        # 输出解析器
        self.query_expansion_parser = QueryExpansionOutput()
        self.score_parser = PaperScoreOutput()
    
    async def expand_query(self, user_requirement: str) -> str:
        """
        查询扩展 - 使用 LangChain Chain
        """
        # 定义 Prompt 模板
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                "你是一个科研检索助手。用户的查询是企业侧的\"业务需求\"，请将其转化为学术界的\"科研术语\"。"
            ),
            HumanMessagePromptTemplate.from_template(
                """用户需求："{requirement}"

请做两件事：
1. 提取或推断 3-5 个核心学术关键词（英文）。
2. 生成一段 50 字左右的"假设性论文摘要"（英文），描述一篇能完美解决该问题的论文应该长什么样。

返回格式：关键词1, 关键词2, 关键词3. [Abstract]: 假设性摘要内容...
不要返回其他废话，直接返回增强后的文本。"""
            )
        ])
        
        # 创建 Chain
        chain = prompt | self.llm | self.query_expansion_parser
        
        try:
            # 执行 Chain
            result = await chain.ainvoke({"requirement": user_requirement})
            logger.info(f"查询扩展: {user_requirement} -> {result[:50]}...")
            return result
        except Exception as e:
            logger.warning(f"查询扩展失败，使用原始查询: {e}")
            return user_requirement
    
    async def score_paper(self, user_requirement: str, paper_title: str, paper_abstract: str) -> Dict:
        """
        论文评分 - 使用 LangChain Chain + Output Parser
        """
        # 定义 Prompt 模板
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                """你是一位严苛的企业技术转移专家（Technology Transfer Officer）。
你的任务是评估一篇学术论文是否具备转化为企业解决方案的潜力。
请摒弃学术客套，采用"尽职调查"的严厉眼光进行通过/不通过（Pass/Fail）评审。"""
            ),
            HumanMessagePromptTemplate.from_template(
                """### 评估任务
企业需求：
"{requirement}"

待评审论文：
标题：{title}
摘要：{abstract}

### 评分标准 (0-100分)
请严格按照以下档位打分，**严禁给中间分**（如不要给 65, 75 这种模糊分）：

- **[90-100] 完美适配 (S级)**: 论文的方法直接解决了该痛点，且技术路线成熟（如已有代码实现、工业数据集验证），几乎可以直接落地。
- **[75-89] 技术强相关 (A级)**: 核心算法对口，但场景可能不同（例如：需求是工业质检，论文是医学影像检测，但方法通用），需要一定的迁移成本。
- **[40-74] 理论相关 (B级)**: 属于同一大领域（如都是CV），但具体任务不匹配，或者论文太偏纯理论，落地难度大。
- **[0-39] 噪音/不相关 (C级)**: 关键词虽然匹配（如都有"AI"），但解决的是完全不同的问题。

### 输出要求
请先在内心进行批判性思考（Chain of Thought），然后输出 JSON：
{{
    "score": <int 0-100>,
    "reason": "<一句话犀利点评，指出最大的亮点或最大的缺陷>"
}}"""
            )
        ])
        
        # 创建 Chain（包含输出解析）
        chain = prompt | self.llm | self.score_parser
        
        try:
            result = await chain.ainvoke({
                "requirement": user_requirement,
                "title": paper_title,
                "abstract": paper_abstract
            })
            return result
        except Exception as e:
            logger.error(f"评分出错: {e}")
            return {"score": 0, "reason": "评分服务异常"}


# ==================== 使用 LangGraph 实现复杂工作流 ====================

class MatchingState(TypedDict):
    """匹配工作流的状态"""
    user_requirement: str
    expanded_query: str
    vector_results: List[Dict]
    paper_details: List[Dict]
    ranked_results: List[Dict]
    final_output: List[Dict]

def create_matching_graph():
    """
    使用 LangGraph 创建匹配工作流
    
    工作流节点：
    1. Query Expansion（查询扩展）
    2. Vector Search（向量检索）
    3. Data Hydration（数据填充）
    4. LLM Re-ranking（精排）
    5. Final Output（最终输出）
    """
    
    # 定义状态图
    workflow = StateGraph(MatchingState)
    
    # 节点 1: Query Expansion
    async def expand_query_node(state: MatchingState):
        """查询扩展节点"""
        from services.llm_service_langchain import LLMServiceLangChain
        llm_service = LLMServiceLangChain()
        expanded = await llm_service.expand_query(state["user_requirement"])
        return {"expanded_query": expanded}
    
    # 节点 2: Vector Search
    async def vector_search_node(state: MatchingState):
        """向量检索节点"""
        from services.vector_service import get_vector_service
        vector_service = get_vector_service()
        results = vector_service.search_similar(state["expanded_query"], top_k=50)
        return {"vector_results": results}
    
    # 节点 3: Data Hydration
    async def hydrate_data_node(state: MatchingState):
        """数据填充节点"""
        from database.database import get_db_connection
        paper_ids = [p[0] for p in state["vector_results"]]
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(paper_ids))
        query = f"SELECT * FROM papers WHERE arxiv_id IN ({placeholders})"
        cursor.execute(query, paper_ids)
        rows = cursor.fetchall()
        conn.close()
        
        row_dict = {row["arxiv_id"]: row for row in rows}
        paper_details = []
        for pid, vec_score in state["vector_results"]:
            if pid in row_dict:
                row = row_dict[pid]
                paper_details.append({
                    "paper_id": pid,
                    "title": row["title"],
                    "abstract": row["abstract"],
                    "authors": row["authors"],
                    "vector_score": vec_score
                })
        return {"paper_details": paper_details}
    
    # 节点 4: LLM Re-ranking
    async def rerank_node(state: MatchingState):
        """LLM 重排序节点"""
        from services.llm_service_langchain import LLMServiceLangChain
        llm_service = LLMServiceLangChain()
        
        # 只对 Top-20 进行精排
        target_papers = state["paper_details"][:20]
        ranked_results = []
        
        # Listwise 批处理
        batch_size = 5
        for i in range(0, len(target_papers), batch_size):
            batch = target_papers[i:i + batch_size]
            # 这里可以调用 Listwise 评分
            # 简化示例，实际需要实现 Listwise 逻辑
            for paper in batch:
                score_result = await llm_service.score_paper(
                    state["user_requirement"],
                    paper["title"],
                    paper["abstract"]
                )
                ranked_results.append({
                    "paper_id": paper["paper_id"],
                    "score": score_result["score"],
                    "reason": score_result["reason"]
                })
        
        ranked_results.sort(key=lambda x: x["score"], reverse=True)
        return {"ranked_results": ranked_results}
    
    # 节点 5: Final Output
    async def final_output_node(state: MatchingState):
        """最终输出节点"""
        detail_map = {p["paper_id"]: p for p in state["paper_details"]}
        final_output = []
        for res in state["ranked_results"]:
            pid = res["paper_id"]
            if pid in detail_map:
                paper = detail_map[pid]
                final_output.append({
                    **paper,
                    "score": res["score"],
                    "reason": res["reason"]
                })
        return {"final_output": final_output}
    
    # 添加节点
    workflow.add_node("expand_query", expand_query_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("hydrate_data", hydrate_data_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("final_output", final_output_node)
    
    # 定义边（工作流）
    workflow.set_entry_point("expand_query")
    workflow.add_edge("expand_query", "vector_search")
    workflow.add_edge("vector_search", "hydrate_data")
    workflow.add_edge("hydrate_data", "rerank")
    workflow.add_edge("rerank", "final_output")
    workflow.add_edge("final_output", END)
    
    return workflow.compile()


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""
    # 方式 1: 使用 LangChain Chain（简单场景）
    llm_service = LLMServiceLangChain()
    expanded = await llm_service.expand_query("工业质检")
    score = await llm_service.score_paper("工业质检", "论文标题", "论文摘要")
    
    # 方式 2: 使用 LangGraph 工作流（复杂场景）
    graph = create_matching_graph()
    result = await graph.ainvoke({
        "user_requirement": "工业质检",
        "expanded_query": "",
        "vector_results": [],
        "paper_details": [],
        "ranked_results": [],
        "final_output": []
    })
    print(result["final_output"])

