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
    
    async def expand_paper_to_scenarios(self, paper_title: str, paper_abstract: str) -> str:
        """
        将学术论文扩展为企业应用场景
        """
        prompt = f"""
        你是一位技术商业化专家。请分析以下学术论文，并指出它可能解决哪些企业实际需求。
        
        论文标题：{paper_title}
        论文摘要：{paper_abstract}
        
        请做两件事：
        1. 列出3-5个可能的应用行业（如：制造业、医疗、金融等）
        2. 生成一段"企业应用场景描述"，说明这项技术能解决什么具体问题
        
        返回格式：行业1, 行业2, 行业3. [场景]: 应用场景描述...
        """
        
        try:
            content = await self._call_deepseek(
                [{"role": "user", "content": prompt}],
                temperature=0.7,
                force_json=False
            )
            return content
        except Exception as e:
            logger.warning(f"论文场景扩展失败: {e}")
            return f"通用技术"
    
    async def score_requirements_for_paper(
        self, 
        paper_title: str,
        paper_abstract: str,
        paper_categories: str,
        requirements: List[Dict]
    ) -> List[Dict]:
        """
        评估论文与需求的匹配度（Listwise批量评估）
        """
        if not self.api_key:
            return self._get_default_scores(requirements)
        
        # 构建批量评估的Prompt
        requirements_text = ""
        for idx, req in enumerate(requirements, 1):
            requirements_text += f"""
[需求 {idx} - ID: {req['requirement_id']}]
标题: {req['title']}
行业: {req['industry']}
痛点: {req['pain_points'][:200]}...
技术难度: {req['technical_level']}
市场规模: {req['market_size']}

---
"""
        
        system_prompt = """你是一位资深的技术转移顾问，负责评估科研成果的商业化潜力。请从市场需求、技术适配度、实施难度、商业价值等维度进行综合评估。"""
        
        user_prompt = f"""
### 评估任务
待评估的科研成果：
标题：{paper_title}
摘要：{paper_abstract}
领域：{paper_categories}

### 候选需求列表
{requirements_text}

### 评分标准 (0-100分)
- **[90-100] 直接落地 (S级)**: 论文技术直接解决该需求痛点，无需大改，市场明确
- **[75-89] 高价值适配 (A级)**: 核心算法对口，需一定适配但商业价值高
- **[60-74] 需技术适配 (B级)**: 相关但需较大技术改造，有潜在价值
- **[40-59] 理论相关 (C级)**: 同一技术领域，但解决的是不同问题
- **[0-39] 关联性弱 (D级)**: 基本不相关，强行匹配

### 额外要求
为每个匹配需求提供简短的"实施建议"（50字内），说明如何将技术应用到该需求中。

### 输出格式
返回JSON数组：
[
    {{
        "requirement_id": "需求ID",
        "score": 85,
        "reason": "详细匹配理由...",
        "implementation_suggestion": "实施建议..."
    }}
]
"""
        
        try:
            content = await self._call_deepseek([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.7, max_tokens=2000, force_json=False)
            
            # 解析结果
            import json
            data = json.loads(content)
            
            # 返回排序后的结果
            return sorted(data, key=lambda x: x["score"], reverse=True)
            
        except Exception as e:
            logger.error(f"需求评分失败: {e}")
            return self._get_default_scores(requirements)
    
    def _get_default_scores(self, requirements: List[Dict]) -> List[Dict]:
        """基于向量相似度生成有意义的评分和理由"""
        results = []
        
        for req in requirements:
            # 获取向量分数（从传入的requirements中获取）
            vector_score = req.get("vector_score", 0)
            
            # 将0-1的向量分数转换为0-100
            score = min(100, int(vector_score * 120))
            
            # 从需求中提取关键信息
            industry = req.get("industry", "")
            technical_level = req.get("technical_level", "")
            market_size = req.get("market_size", "")
            pain_points = req.get("pain_points", "")
            
            # 生成有意义的推荐理由
            reason = self._generate_reason_from_requirement(
                score, industry, technical_level, market_size, pain_points
            )
            
            # 生成实施建议
            suggestion = self._generate_suggestion_from_requirement(
                score, industry, technical_level, market_size
            )
            
            # 确定匹配类型
            match_type = self._get_match_type_from_score(score)
            
            results.append({
                "requirement_id": req["requirement_id"],
                "score": score,
                "reason": reason,
                "implementation_suggestion": suggestion,
                "match_type": match_type
            })
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def _generate_reason_from_requirement(self, score, industry, technical_level, market_size, pain_points):
        """根据需求信息生成推荐理由"""
        
        if score >= 80:
            base = "高匹配度：技术方案与需求高度契合"
        elif score >= 60:
            base = "中等匹配度：技术方案与需求有一定相关性"
        elif score >= 40:
            base = "理论相关：属于同一技术领域"
        else:
            base = "关联性较弱：向量相似度较低"
        
        # 添加行业信息
        if industry:
            base += f"，涉及{industry}行业"
        
        # 添加技术难度信息
        if technical_level:
            if technical_level in ["高", "极高"]:
                base += "，技术实施难度较高"
            elif technical_level == "中":
                base += "，技术实施难度适中"
            else:
                base += "，技术实施难度较低"
        
        # 添加市场规模信息
        if market_size:
            if market_size in ["大型", "超大型"]:
                base += "，市场潜力大"
            elif market_size == "中型":
                base += "，市场潜力中等"
            else:
                base += "，市场相对细分"
        
        # 如果有痛点信息，可以提取关键词
        if pain_points:
            keywords = ["数据", "系统", "安全", "成本", "效率", "人才", "集成"]
            found = [kw for kw in keywords if kw in pain_points]
            if found:
                base += f"，主要涉及{', '.join(found[:2])}等方面的问题"
        
        return base

    def _generate_suggestion_from_requirement(self, score, industry, technical_level, market_size):
        """根据需求信息生成实施建议"""
        
        if score >= 80:
            base = "建议直接进行技术对接，可考虑开展试点项目"
        elif score >= 60:
            base = "建议进行详细技术评估，制定适配方案"
        elif score >= 40:
            base = "建议进一步分析技术契合度，评估商业可行性"
        else:
            base = "建议寻找更匹配的技术方案或调整需求方向"
        
        # 根据技术难度添加建议
        if technical_level in ["高", "极高"]:
            base += "。由于技术难度较高，建议组建专家团队进行技术攻关"
        elif technical_level == "中":
            base += "。建议分阶段实施，先解决核心问题"
        elif technical_level in ["低", "简单"]:
            base += "。实施难度较低，可快速推进"
        
        # 根据市场规模添加建议
        if market_size in ["大型", "超大型"]:
            base += "。市场规模较大，建议制定长期发展规划"
        elif market_size == "中型":
            base += "。建议从小规模试点开始，逐步扩大"
        else:
            base += "。市场相对细分，建议精准定位目标客户"
        
        return base

    def _get_match_type_from_score(self, score):
        """根据分数确定匹配类型"""
        if score >= 90:
            return "S级-直接落地"
        elif score >= 75:
            return "A级-高价值适配"
        elif score >= 60:
            return "B级-需技术适配"
        elif score >= 40:
            return "C级-理论相关"
        else:
            return "D级-关联性弱"

# 单例模式保持不变...
_llm_service = None
def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service