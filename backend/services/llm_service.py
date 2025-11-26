"""
LLM 服务 - 整合专家级评分提示词
"""
import logging
import os
import json
import re
import random
from typing import Dict, List
import httpx
import asyncio

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.api_base = "https://api.deepseek.com/v1/chat/completions"
        # 增加并发限制，防止触发 API 速率限制
        self.sem = asyncio.Semaphore(5) 

    async def _call_deepseek(self, messages: List[Dict], temperature: float = 0.3, max_tokens: int = 500, force_json: bool = True) -> str:
        """
        封装底层的 API 调用
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数（Listwise 模式需要更多）
            force_json: 是否强制 JSON 格式（Listwise 返回数组，不需要强制）
        """
        if not self.api_key:
            raise ValueError("API Key not found")
        
        json_config = {"response_format": {"type": "json_object"}} if force_json else {}
            
        async with httpx.AsyncClient(timeout=60.0) as client:  # Listwise 可能需要更长时间
            request_body = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **json_config
            }
            
            response = await client.post(
                self.api_base,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=request_body
            )
            
            # 如果请求失败，记录详细的错误信息
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"DeepSeek API 请求失败: {response.status_code}")
                logger.error(f"请求体: {request_body}")
                logger.error(f"错误详情: {error_detail}")
                response.raise_for_status()
            
            return response.json()["choices"][0]["message"]["content"]

    async def expand_query(self, user_requirement: str) -> str:
        """
        [粗排优化] 查询扩展 (Query Expansion)
        将用户的企业需求转化为 3-5 个学术关键词和一段假设性摘要。
        """
        prompt = f"""
        你是一个科研检索助手。用户的查询是企业侧的“业务需求”，请将其转化为学术界的“科研术语”。
        
        用户需求："{user_requirement}"
        
        请做两件事：
        1. 提取或推断 3-5 个核心学术关键词（英文）。
        2. 生成一段 50 字左右的“假设性论文摘要”（英文），描述一篇能完美解决该问题的论文应该长什么样。
        
        返回格式：关键词1, 关键词2, 关键词3. [Abstract]: 假设性摘要内容...
        不要返回其他废话，直接返回增强后的文本。
        """
        try:
            # 使用简单的 prompt 快速生成
            # force_json=False 因为返回的是纯文本，不是 JSON
            content = await self._call_deepseek(
                [{"role": "user", "content": prompt}], 
                temperature=0.7,
                force_json=False
            )
            logger.info(f"查询扩展: {user_requirement} -> {content[:50]}...")
            return content
        except Exception as e:
            logger.warning(f"查询扩展失败，使用原始查询: {e}")
            return user_requirement

    async def score_paper(self, user_requirement: str, paper_title: str, paper_abstract: str) -> Dict:
        """
        [精排优化] 专家级评分
        """
        if not self.api_key:
            return {"score": 50, "reason": "API未配置"}

        # === 核心提示词优化 ===
        system_prompt = """你是一位严苛的企业技术转移专家（Technology Transfer Officer）。
你的任务是评估一篇学术论文是否具备转化为企业解决方案的潜力。
请摒弃学术客套，采用“尽职调查”的严厉眼光进行通过/不通过（Pass/Fail）评审。"""

        user_prompt = f"""
### 评估任务
企业需求：
"{user_requirement}"

待评审论文：
标题：{paper_title}
摘要：{paper_abstract}

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
    "reason": "<结合论文和需求非常详细的点评，指出最大的亮点或最大的缺陷，并给出具体的结合建议，这个技术在整个需求工程化中的作用>"
}}
"""
        try:
            async with self.sem: # 并发控制
                content = await self._call_deepseek([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ])
                
            data = json.loads(content)
            return {
                "score": data.get("score", 0),
                "reason": data.get("reason", "解析失败")
            }
        except Exception as e:
            logger.error(f"评分出错: {e}")
            return {"score": 0, "reason": "评分服务异常"}

    async def score_papers_listwise(self, user_requirement: str, papers_batch: List[Dict]) -> List[Dict]:
        """
        Listwise 评分：一次性把多篇论文发给 LLM，让它在内部对比打分
        这样可以更准确地评估相对质量，速度也更快
        """
        if not self.api_key:
            # 如果没有 API key，返回默认分数
            return [
                {
                    "paper_id": p["paper_id"],
                    "score": round(random.uniform(30, 60), 2),
                    "reason": "API未配置，返回默认分数"
                }
                for p in papers_batch
            ]
        
        # 构建包含多篇论文的 Prompt
        papers_text = ""
        for idx, p in enumerate(papers_batch, 1):
            papers_text += f"""
[论文 {idx} - ID: {p['paper_id']}]
标题: {p['title']}
摘要: {p['abstract'][:400] if len(p.get('abstract', '')) > 400 else p.get('abstract', '')}...

---
"""
        
        system_prompt = """你是一位严苛的企业技术转移专家。你的任务是评估一篇学术论文是否具备转化为企业解决方案的潜力。你需要同时评估多篇候选论文，通过对比分析给出相对准确的评分。"""
        
        user_prompt = f"""
### 评估任务
企业需求：
"{user_requirement}"

### 候选论文列表
{papers_text}

### 评分要求
请仔细对比这 {len(papers_batch)} 篇论文，根据它们与用户需求的匹配度进行评分。

**评分标准 (0-100分)**：
- **[90-100] 完美适配 (S级)**: 论文的方法直接解决了该痛点，且技术路线成熟（如已有代码实现、工业数据集验证），几乎可以直接落地。
- **[75-89] 技术强相关 (A级)**:  核心算法对口，但场景可能不同（例如：需求是工业质检，论文是医学影像检测，但方法通用），需要一定的迁移成本。
- **[40-74] 理论相关 (B级)**: 属于同一大领域（如都是CV），但具体任务不匹配，或者论文太偏纯理论，落地难度大。
- **[0-39] 噪音/不相关 (C级)**: 关键词虽然匹配（如都有"AI"），但解决的是完全不同的问题。

**重要**：请通过对比分析，给出有区分度的分数，避免所有论文分数相同。

### 输出格式
请返回 JSON 数组，每篇论文包含 id, score, reason：
[
    {{"id": "论文ID", "score": 85, "reason": "结合论文和需求非常详细的点评，指出最大的亮点或最大的缺陷，并给出具体的结合建议，这个技术在整个需求工程化中的作用"}},
    {{"id": "论文ID", "score": 60, "reason": "结合论文和需求非常详细的点评，指出最大的亮点或最大的缺陷，并给出具体的结合建议，这个技术在整个需求工程化中的作用"}}
]
"""
        
        try:
            async with self.sem:  # 并发控制
                # Listwise 模式返回数组，不需要强制 json_object，且需要更多 tokens
                content = await self._call_deepseek([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ], temperature=0.7, max_tokens=1500, force_json=False)  # 提高温度，增加 tokens，不强制 JSON 格式
            
            # 解析 JSON 响应
            try:
                # 尝试直接解析 JSON
                data = json.loads(content)
            except json.JSONDecodeError:
                # 如果失败，尝试提取 JSON 部分
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError(f"无法解析 JSON: {content[:200]}")
            
            # 确保返回的是列表
            if not isinstance(data, list):
                data = [data]
            
            # 构建结果列表
            results = []
            paper_id_map = {p["paper_id"]: p for p in papers_batch}
            
            for item in data:
                paper_id = item.get("id") or item.get("paper_id")
                if paper_id and paper_id in paper_id_map:
                    score = int(item.get("score", 50))
                    # 确保分数在 0-100 范围内
                    score = max(0, min(100, score))
                    results.append({
                        "paper_id": paper_id,
                        "score": score,
                        "reason": item.get("reason", "未提供理由")
                    })
            
            # 如果解析失败，为所有论文返回默认分数
            if len(results) != len(papers_batch):
                logger.warning(f"Listwise 解析不完整: 期望 {len(papers_batch)} 篇，实际 {len(results)} 篇")
                # 为缺失的论文补充默认分数
                parsed_ids = {r["paper_id"] for r in results}
                for p in papers_batch:
                    if p["paper_id"] not in parsed_ids:
                        results.append({
                            "paper_id": p["paper_id"],
                            "score": 50,
                            "reason": "解析失败，使用默认分数"
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Listwise 评分失败: {e}")
            # 返回默认分数
            return [
                {
                    "paper_id": p["paper_id"],
                    "score": round(random.uniform(30, 60), 2),
                    "reason": f"评分失败: {str(e)[:100]}"
                }
                for p in papers_batch
            ]

    async def score_papers_batch(self, user_requirement: str, papers: List[Dict]) -> List[Dict]:
        """
        优化后的批处理逻辑：结合截断策略 + Listwise 排序
        
        策略：
        1. 截断策略：只对向量搜索的前 20 篇进行 LLM 精排（节省成本和时间）
        2. Listwise 排序：每 5 篇论文一组，让 LLM 内部对比打分（提升准确性和速度）
        """
        if not papers:
            return []
        
        # ===== 方案 A：截断策略 =====
        # 向量搜索已经做了初步排序，通常前 20 篇最有价值
        # 只对前 20 篇进行 LLM 精排，节省 API 调用成本
        top_n = 5
        target_papers = papers[:top_n]
        
        logger.info(f"向量召回 {len(papers)} 篇，仅对前 {len(target_papers)} 篇进行 LLM 精排")
        
        if not self.api_key:
            # 如果没有 API key，返回默认分数
            logger.warning("未设置 DEEPSEEK_API_KEY，返回默认分数")
            return [
                {
                    "paper_id": p["paper_id"],
                    "score": round(random.uniform(30, 60), 2),
                    "reason": "API未配置，返回默认分数"
                }
                for p in target_papers
            ]
        
        # ===== 方案 B：Listwise 排序 =====
        # 将论文分成每组 5 篇的批次，让 LLM 在内部对比打分
        batch_size = 5
        all_results = []
        
        for i in range(0, len(target_papers), batch_size):
            batch = target_papers[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(target_papers) + batch_size - 1) // batch_size
            
            logger.info(f"正在处理批次 {batch_num}/{total_batches} ({len(batch)} 篇论文)...")
            
            # 调用 Listwise 评分
            batch_results = await self.score_papers_listwise(user_requirement, batch)
            all_results.extend(batch_results)
        
        # 按分数排序（从高到低）
        all_results.sort(key=lambda x: x["score"], reverse=True)

        print(all_results)
        # 统计信息
        scores = [r["score"] for r in all_results]
        unique_scores = len(set(scores))
        score_range = (min(scores), max(scores)) if scores else (0, 0)
        
        logger.info(f"LLM 精排完成: 处理 {len(all_results)} 篇，唯一分数数={unique_scores}，分数范围={score_range}")
        
        if unique_scores < len(all_results) * 0.3:
            logger.warning(f"警告: 评分区分度较低，{len(all_results)}篇论文中只有{unique_scores}个不同的分数")
        
        return all_results

# 单例模式保持不变...
_llm_service = None
def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service