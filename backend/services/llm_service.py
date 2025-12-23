"""
LLM 服务 - 整合专家级评分提示词
"""
import logging
import os
import json
import re
import random
import time
from typing import Dict, List, Optional
import httpx
import asyncio

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.api_base = "https://api.deepseek.com/v1/chat/completions"
        # 增加并发限制，防止触发 API 速率限制
        self.sem = asyncio.Semaphore(5) 
        self.client = httpx.AsyncClient(
            timeout=600.0,
            headers={"Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"}
        )

    async def close(self):
        await self.client.aclose()
    @staticmethod
    def _clean_json_string(content: str) -> str:
        """
        清洗 LLM 返回的 JSON 字符串，去掉 ```json ``` 等 Markdown 包裹
        """
        if not isinstance(content, str):
            return content
        text = content.strip()
        # 去掉前缀 ```json 或 ```
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        # 去掉结尾 ```
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    @staticmethod
    def _smart_truncate_pdf(text: str, max_len: int = 8000) -> str:
        """
        智能截断 PDF 文本：保留开头+中间+结尾，尽量覆盖 Method / Experiments 区域
        """
        if not text:
            return text
        total_len = len(text)
        if total_len <= max_len:
            return text

        # 头部：摘要 + 引言
        head_len = 2000
        # 尾部：实验 + 结论
        tail_len = 1000
        # 中部：方法 + 实验主体
        mid_len = max_len - head_len - tail_len
        mid_start = max(total_len // 3, head_len)
        mid_end = min(mid_start + mid_len, total_len - tail_len)

        part1 = text[:head_len]
        part2 = text[mid_start:mid_end]
        part3 = text[-tail_len:]

        return (
            part1
            + "\n...[Skipped Middle]...\n"
            + part2
            + "\n...[Skipped Tail]...\n"
            + part3
        )

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
        
        request_body = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **json_config
            }
            
        response = await self.client.post(
                self.api_base,
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

    async def classify_paper_type(
        self,
        paper_title: str,
        paper_abstract: str,
        intro_snippet: str = ""
    ) -> str:
        """
        轻量级论文体裁分类器
        返回: method | system | survey | benchmark | industry | theory
        """
        if not self.api_key:
            return "method"

        system_prompt = """
你是一个学术论文体裁分类器。
请根据标题、摘要和引言片段，判断论文属于下面哪一类：
- method: 提出新的模型/算法/训练范式
- system: 系统架构、工程方法论、软件工程/平台设计
- survey: 综述 / review / roadmap
- benchmark: 数据集、基准、评测框架
- industry: 工业界经验报告 / 大规模部署案例
- theory: 偏数学/理论分析（收敛性、复杂度等）
只返回一个单词：method / system / survey / benchmark / industry / theory
""".strip()

        user_prompt = f"""
标题: {paper_title}
摘要: {paper_abstract}
引言片段: {intro_snippet[:1500]}
"""

        try:
            content = await self._call_deepseek(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=10,
                force_json=False,
            )
            label = content.strip().lower()
            for t in ["method", "system", "survey", "benchmark", "industry", "theory"]:
                if t in label:
                    return t
            return "method"
        except Exception as e:
            logger.warning(f"论文体裁分类失败，默认使用 method: {e}")
            return "method"

    async def expand_query(self, user_requirement: str) -> str:
        """
        [粗排优化] 查询扩展 (Query Expansion) v2.0
        策略：业务需求 -> 技术映射（多路径枚举） -> 混合检索词
        """
        prompt = f"""
        你是一位精通人工智能领域的首席架构师。用户的输入是企业侧的"业务痛点"。
        请你将其转化为学术界可能用于解决该问题的"具体技术路线"和"专业术语"。

        用户需求："{user_requirement}"

        **重要：首先判断输入是否有意义**
        - 如果输入是随机字符组合（如 "asbdkasjbdiubqbuibd"）、重复字符（如 "aaaaa"）或其他无意义的文本，请直接返回 "[INVALID_INPUT]"，不要进行技术术语扩展。
        - 只有确认输入是有意义的业务需求或技术问题描述时，才进行后续的技术术语扩展。

        如果输入有意义，请遵循以下步骤思考：
        1. 分析痛点：用户到底想要什么？（例如：降本、提速、长文本、多模态）
        2. **枚举技术路径（关键）**：列出 3-5 种能解决该问题的**不同技术流派**。不要只给通用的词（如 "Efficient"），要给具体的方案（如 "Quantization", "Speculative Decoding", "Knowledge Distillation", "Linear Attention", "SNN", "Non-autoregressive" 等）。
        3. 构造增强查询：将这些具体的术语组合成一段文本。

        请严格按照以下格式返回（不要包含 Markdown 格式，不要换行，直接返回一段纯文本）：
        - 如果输入无意义：直接返回 "[INVALID_INPUT]"
        - 如果输入有意义：[Keywords]: <技术术语1>, <技术术语2>, <技术术语3>, <技术术语4>, <技术术语5>. [Context]: <一段包含上述技术术语的学术综述风格的描述，涵盖多种可能的技术解决方案>

        示例输入（有意义）："我想让大模型在手机上跑得快一点"
        示例返回：[Keywords]: Model Quantization, Knowledge Distillation, Edge Computing, MobileNets, Sparse Attention. [Context]: Research on deploying Large Language Models on edge devices focuses on reducing memory footprint and latency. Key approaches include post-training quantization (PTQ) to low-bit precision, structured pruning to enforce sparsity, and architectural innovations like linear attention mechanisms or state-space models (SSMs) to reduce computational complexity.

        示例输入（无意义）："asbdkasjbdiubqbuibd"
        示例返回：[INVALID_INPUT]
        """
        
        try:
            # 适当调高 temperature，鼓励 LLM 发散思维，想出更多冷门技术词
            content = await self._call_deepseek(
                [{"role": "user", "content": prompt}], 
                temperature=0.8, 
                force_json=False
            )
            # 去除可能产生的换行符，保证是一行
            content = content.replace("\n", " ").strip()
            logger.info(f"查询扩展(v2): {user_requirement}... -> {content}...")
            return content
        except Exception as e:
            logger.warning(f"查询扩展失败: {e}")
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
        Listwise 评分：一次性把多篇论文摘要发给 LLM，让它在内部对比打分
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
        top_n = 10
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
        # 这里使用 asyncio.gather 并发处理多个批次，具体并发度仍由 self.sem 控制
        batch_size = 5
        all_results: List[Dict] = []

        batches = []
        for i in range(0, len(target_papers), batch_size):
            batch = target_papers[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(target_papers) + batch_size - 1) // batch_size
            batches.append((batch_num, total_batches, batch))

        logger.info(f"准备并发处理 {len(batches)} 个批次，每批最多 {batch_size} 篇论文")

        # 并发调用 Listwise 评分；self.sem 会限制实际的 API 并发度
        tasks = [
            self.score_papers_listwise(user_requirement, batch)
            for (_batch_num, _total_batches, batch) in batches 
            #内层生成 tasks 的时候，其实 只需要 batch，不需要 batch_num 和 total_batches，但解包时必须写三个变量，于是就用 _batch_num, _total_batches 表示“解包出来但故意不使用”。变量名前加 _，表示“这里有这个值，但后面不会用它，只是为了结构完整/代码可读”。
        ]
        batch_results_list = await asyncio.gather(*tasks, return_exceptions=True)

        for (batch_num, total_batches, batch), result in zip(batches, batch_results_list):
            if isinstance(result, Exception):
                logger.error(
                    f"批次 {batch_num}/{total_batches} ({len(batch)} 篇论文) 打分失败: {result}"
                )
                continue

            logger.info(f"批次 {batch_num}/{total_batches} ({len(batch)} 篇论文) 打分完成")
            all_results.extend(result)
        
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
        achievement_text: str,  # 用户输入的成果文字
        requirements: List[Dict]
    ) -> List[Dict]:
        """
        评估成果与需求的匹配度（优化版：截断+分批+并发，与score_papers_batch一致）
        """
        if not requirements:
            return []
        
        if not self.api_key:
            return self._get_default_scores(requirements)
        
        # ===== 优化策略1：截断策略 =====
        # 向量搜索已经做了初步排序，通常前10个最有价值
        # 只对前10个进行LLM评估，节省API调用成本和时间
        top_n = 10
        target_requirements = requirements[:top_n]
        
        logger.info(f"向量召回 {len(requirements)} 个需求，仅对前 {len(target_requirements)} 个进行LLM评估")
        
        # ===== 优化策略2：分批处理 =====
        # 将需求分成每组5个的批次，让LLM在内部对比打分
        batch_size = 5
        batches = []
        for i in range(0, len(target_requirements), batch_size):
            batch = target_requirements[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(target_requirements) + batch_size - 1) // batch_size
            batches.append((batch_num, total_batches, batch))
        
        logger.info(f"准备并发处理 {len(batches)} 个批次，每批最多 {batch_size} 个需求")
        
        # ===== 优化策略3：并发调用 =====
        # 并发处理多个批次；self.sem 会限制实际的API并发度
        tasks = [
            self._score_requirements_batch(achievement_text, batch)
            for (_batch_num, _total_batches, batch) in batches
        ]
        batch_results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_results: List[Dict] = []
        for (batch_num, total_batches, batch), result in zip(batches, batch_results_list):
            if isinstance(result, Exception):
                logger.error(
                    f"批次 {batch_num}/{total_batches} ({len(batch)} 个需求) 评分失败: {result}"
                )
                # 失败时使用默认分数
                all_results.extend(self._get_default_scores(batch))
                continue
            
            logger.info(f"批次 {batch_num}/{total_batches} ({len(batch)} 个需求) 评分完成")
            all_results.extend(result)
        
        # 按分数排序（从高到低）
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        # 统计信息
        scores = [r["score"] for r in all_results]
        unique_scores = len(set(scores))
        score_range = (min(scores), max(scores)) if scores else (0, 0)
        
        logger.info(f"LLM评估完成: 处理 {len(all_results)} 个需求，唯一分数数={unique_scores}，分数范围={score_range}")
        
        return all_results
    
    async def _score_requirements_batch(
        self,
        achievement_text: str,
        requirements_batch: List[Dict]
    ) -> List[Dict]:
        """
        处理单个批次的需求评分（内部方法）
        """
        # 构建批量评估的Prompt
        requirements_text = ""
        for idx, req in enumerate(requirements_batch, 1):
            pain_points = req.get('pain_points', '') or ''
            description = req.get('description', '') or ''
            # 使用完整的description，因为其中包含了技术特征关键词
            requirements_text += f"""
[需求 {idx} - ID: {req['requirement_id']}]
标题: {req['title']}
行业: {req.get('industry', '')}
描述: {description[:500] if len(description) > 500 else description}
痛点: {pain_points[:300] if len(pain_points) > 300 else pain_points}
技术难度: {req.get('technical_level', '')}
市场规模: {req.get('market_size', '')}

---
"""
        
        system_prompt = """你是一位资深的技术转移顾问，负责评估科研成果的商业化潜力。请从市场需求、技术适配度、实施难度、商业价值等维度进行综合评估。

**关键评估原则**：
1. **技术直接对应性**：成果中的核心技术特征（如"少量示例"、"快速学习"、"无需重新训练"、"跨领域推理"等）是否与需求描述中的技术特征直接对应
2. **避免过度泛化**：不要因为需求涉及"AI"、"机器学习"等通用概念就认为匹配，必须看具体的技术特征是否对应
3. **严格评分**：只有核心技术特征直接对应、能直接解决需求痛点的才给高分（90+），需要较大适配的给中等分数（60-89），仅理论相关的给低分（40-59）"""
        
        user_prompt = f"""
### 评估任务
待评估的科研成果：
{achievement_text}

**请特别注意**：成果中提到的核心技术特征（如"少量示例"、"快速学习"、"无需重新训练"、"跨领域推理"、"精确计算"等）是否与需求描述中的技术特征直接对应。

### 候选需求列表
{requirements_text}

### 评分标准 (0-100分)
- **[90-100] 直接落地 (S级)**: 成果的核心技术特征（如"少量示例快速学习"、"无需重新训练"等）与需求描述中的技术特征**直接对应**，成果技术能直接解决该需求痛点，无需大改
- **[75-89] 高价值适配 (A级)**: 核心技术特征基本对应，需一定适配但商业价值高
- **[60-74] 需技术适配 (B级)**: 部分技术特征相关，需较大技术改造，有潜在价值
- **[40-59] 理论相关 (C级)**: 同一技术领域，但核心技术特征不对应，解决的是不同问题
- **[0-39] 关联性弱 (D级)**: 基本不相关，核心技术特征不对应

**⚠️ 关键要求**：
- 必须检查成果中的核心技术特征（如"少量示例"、"快速学习"、"无需重新训练"、"跨领域推理"等）是否在需求描述中明确体现
- 如果成果研究的是"通过少量示例快速学习"，但需求只是泛泛提到"AI能力不足"，没有明确提到"少量示例"、"快速学习"等特征，则不应给高分
- 只有需求描述中明确包含与成果核心技术特征对应的技术特征时，才给高分

### 额外要求
为每个匹配需求提供简短的"实施建议"（50字内），说明如何将技术应用到该需求中。

**重要**：请通过对比分析，给出有区分度的分数，避免所有需求分数相同。

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
            async with self.sem:  # 并发控制
                content = await self._call_deepseek([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ], temperature=0.7, max_tokens=1500, force_json=False)
            
            # 解析结果
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # 如果失败，尝试提取JSON部分
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError(f"无法解析JSON: {content[:200]}")
            
            # 确保返回的是列表
            if not isinstance(data, list):
                data = [data]
            
            # 构建结果列表
            results = []
            requirement_id_map = {req["requirement_id"]: req for req in requirements_batch}
            
            for item in data:
                req_id = item.get("requirement_id")
                if req_id and req_id in requirement_id_map:
                    score = int(item.get("score", 50))
                    # 确保分数在0-100范围内
                    score = max(0, min(100, score))
                    results.append({
                        "requirement_id": req_id,
                        "score": score,
                        "reason": item.get("reason", "未提供理由"),
                        "implementation_suggestion": item.get("implementation_suggestion", "")
                    })
            
            # 如果解析失败，为所有需求返回默认分数
            if len(results) != len(requirements_batch):
                logger.warning(f"批次解析不完整: 期望 {len(requirements_batch)} 个，实际 {len(results)} 个")
                parsed_ids = {r["requirement_id"] for r in results}
                for req in requirements_batch:
                    if req["requirement_id"] not in parsed_ids:
                        results.append({
                            "requirement_id": req["requirement_id"],
                            "score": 50,
                            "reason": "解析失败，使用默认分数",
                            "implementation_suggestion": ""
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"批次评分失败: {e}")
            # 返回默认分数
            return self._get_default_scores(requirements_batch)
    
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

    async def analyze_paper_pdf(self, paper_title: str, paper_abstract: str, pdf_content: str, user_requirement: str) -> Dict:
        """
        对PDF内容进行精读分析
        
        Args:
            paper_title: 论文标题
            paper_abstract: 论文摘要
            pdf_content: PDF提取的文本内容
            user_requirement: 用户需求
            
        Returns:
            包含分析结果的字典
        """
        if not self.api_key:
            return {"error": "API未配置"}
        
        # 更智能的 PDF 截断策略：保留开头+中间+结尾，尽量覆盖 Method / Experiments
        pdf_content_truncated = self._smart_truncate_pdf(pdf_content, max_len=8000)
        
        system_prompt = """
你是一位世界顶级的AI算法架构师，擅长将学术论文（Paper）进行工程化拆解。
你的任务不是写读后感，而是进行【逆向工程】。你需要从论文中提取出能够指导代码落地的具体参数、公式、数据结构和训练技巧。
如果论文中缺少具体细节，你需要基于行业经验进行合理的【工程推断】并标记出来。
""".strip()
        
        user_prompt = f"""
### 任务背景
用户希望基于此论文解决的具体问题：{user_requirement}

### 输入数据
标题：{paper_title}
摘要：{paper_abstract}
PDF文本片段（截断后）：
{pdf_content_truncated}

### 深度分析指令（Chain of Thought）
请一步步思考，忽略掉背景介绍和客套话，直接挖掘以下硬核信息：
1. **输入/输出契约**：模型的输入具体是什么（张量维度、数据类型）？输出是什么？
2. **核心算法逻辑**：不要只说"用了Transformer"，要说明是几层？Hidden Size是多少？Loss Function具体公式是什么？（如果文本中有）
3. **数据工程**：论文是如何清洗数据的？有没有特殊的增强（Augmentation）手段？
4. **训练细节**：Batch Size, Learning Rate, Optimizer, 显存占用预估。

### 输出格式 (严格JSON)
{{
    "engineering_analysis": {{
        "model_architecture": "描述模型拓扑结构，如：Encoder-Decoder, 3层LSTM等",
        "input_spec": "例如：[Batch, 512, 768] 的Float32张量",
        "loss_function": "例如：CrossEntropy + 0.1 * KL_Divergence",
        "key_hyperparameters": ["LR=1e-4", "Batch=32", "Dropout=0.1"]
    }},
    "implementation_gap": "指出复现这篇论文最大的坑在哪里（例如：数据集未开源、使用了私有硬件等）",
    "reproducibility_score": "1-10分，评估复现难度",
    "code_snippets_inference": "基于理解，生成一段伪代码或Python核心逻辑代码，展示数据流转过程"
}}
""".strip()
        
        try:
            async with self.sem:
                content = await self._call_deepseek(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.5,
                    max_tokens=2000,
                )

            cleaned = self._clean_json_string(content)
            data = json.loads(cleaned)
            return data
            
        except Exception as e:
            logger.error(f"PDF精读分析失败: {e}")
            return {"error": f"分析失败: {str(e)}"}

    # =====================
    # 分类型解析器
    # =====================

    async def _analyze_method_paper(
        self,
        paper_title: str,
        paper_abstract: str,
        pdf_content: str,
        user_requirement: str,
    ) -> Dict:
        """硬核算法/模型类论文解析"""
        logger.info(f"_analyze_method_paper 被调用: {paper_title[:50]}...")
        if not self.api_key:
            logger.warning(f"API key 未配置，返回错误")
            return {"error": "API未配置"}

        logger.info(f"API key 已配置，开始处理 PDF 内容")
        pdf_content_truncated = self._smart_truncate_pdf(pdf_content, max_len=8000)
        logger.info(f"PDF 内容截断完成，长度: {len(pdf_content_truncated)}")

        system_prompt = """
你是一位世界顶级的AI算法架构师，擅长将学术论文（Paper）进行工程化拆解。
你的任务不是写读后感，而是进行【逆向工程】。你需要从论文中提取出能够指导代码落地的具体参数、公式、数据结构和训练技巧。
如果论文中缺少具体细节，你需要基于行业经验进行合理的【工程推断】并标记出来。
""".strip()

        user_prompt = f"""
### 任务背景
用户希望基于此论文解决的具体问题：{user_requirement}

### 输入数据
标题：{paper_title}
摘要：{paper_abstract}
PDF文本片段（截断后）：
{pdf_content_truncated}

### 深度分析指令（Chain of Thought）
请一步步思考，忽略掉背景介绍和客套话，直接挖掘以下硬核信息：
1. 输入/输出契约（Input/Output Spec）：张量维度、数据类型、mask 规则。
2. 核心算法逻辑：模块拓扑（几层、hidden size、子模块）、关键子过程。
3. 数据工程：数据清洗、切分、增强（augmentation）策略。
4. 训练细节：Batch Size, Learning Rate, Optimizer, 正则项、蒸馏/裁剪等 trick。
5. 推理策略：采样方法、近似算法、与标准 LLM 在复杂度/延迟上的对比。

### 输出格式 (严格JSON)
{{
  "big_idea": "一句话概括本论文范式/创新点（工程视角）",
  "engineering_analysis": {{
    "model_architecture": "模块和拓扑结构描述，如: Encoder-Decoder, N 层 Transformer, latent 压缩结构等",
    "input_spec": "例如：[Batch, 512, 768] float32，包含 padding / mask 说明",
    "output_spec": "输出张量形状及含义",
    "loss_function": "损失函数组合及公式说明",
    "key_hyperparameters": ["LR=1e-4", "Batch=32", "Dropout=0.1"]
  }},
  "training_procedure": {{
    "data_processing": "数据来源、清洗、切分、增强方式",
    "optimization": "optimizer, scheduler, warmup 等配置",
    "regularization_tricks": ["KL clipping λ=0.5", "latent dropout p=0.15"]
  }},
  "inference_strategy": {{
    "sampling_method": "如 temperature sampling + rejection sampling 等",
    "latency_estimation": "与标准自回归 LLM 的大致速度/复杂度对比"
  }},
  "reproducibility": {{
    "implementation_gap": "复现时最大的坑（如私有数据、未公开实现细节）",
    "reproducibility_score": "1-10，数字越大越容易复现"
  }}
}}
""".strip()

        try:
            logger.info(f"开始调用 DeepSeek API 进行方法类论文精读: {paper_title[:50]}...")
            logger.info(f"Prompt 长度 - system: {len(system_prompt)}, user: {len(user_prompt)}")
            async with self.sem:
                logger.info(f"获取到 semaphore，开始调用 API")
                t_api_start = time.perf_counter()
                content = await self._call_deepseek(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.5,
                    max_tokens=2200,
                )
                t_api_end = time.perf_counter()
                api_duration_ms = round((t_api_end - t_api_start) * 1000)
                logger.info(f"DeepSeek API 调用完成: {paper_title[:50]}..., 耗时: {api_duration_ms} ms")
            cleaned = self._clean_json_string(content)
            logger.info(f"JSON 清理完成，开始解析")
            data = json.loads(cleaned)
            logger.info(f"JSON 解析完成，返回结果")
            return data
        except Exception as e:
            logger.error(f"方法类论文解析失败: {e}", exc_info=True)
            return {"error": f"方法类解析失败: {str(e)}"}

    async def _analyze_system_paper(
        self,
        paper_title: str,
        paper_abstract: str,
        pdf_content: str,
        user_requirement: str,
    ) -> Dict:
        """系统/架构类论文解析（如 SPL + ML Components）"""
        if not self.api_key:
            return {"error": "API未配置"}

        total_len = len(pdf_content)
        snippet = self._smart_truncate_pdf(pdf_content, max_len=6000)

        system_prompt = """
你是一位大规模分布式系统与 MLOps 方向的架构师。
你的任务是从系统/软件工程类论文中提取：模块划分、接口契约、运行时策略和监控/回滚机制。
""".strip()

        user_prompt = f"""
### 业务背景
目标业务需求：{user_requirement}

### 论文信息
标题：{paper_title}
摘要：{paper_abstract}
正文片段：
{snippet}

### 解析要求
请重点关注：
- 系统由哪些模块组成？各自职责是什么？
- 模块之间通过什么接口通信？输入输出契约如何？
- 如何管理 ML 组件的非确定性、性能波动与概念漂移？
- 监控指标、阈值及自动替换 / fallback 策略。

### 输出格式 (严格JSON)
{{
  "core_problem": "一句话说明系统想解决的工程痛点",
  "system_components": [
    {{
      "name": "组件名称",
      "responsibility": "该组件的职责",
      "inputs": ["输入源1", "输入源2"],
      "outputs": ["输出1", "输出2"],
      "interfaces": ["例如: gRPC /monitor/report", "Kafka topic: ml_metrics"]
    }}
  ],
  "variation_modeling": {{
    "feature_model_type": "如 probabilistic / boolean / multi-valued",
    "feature_attributes": ["accuracy_range", "context_sensitivity", "confidence_intervals"]
  }},
  "model_contracts": {{
    "required_fields": ["spl_reusability_profile", "operational_requirements", "performance_metrics"]
  }},
  "runtime_policies": {{
    "monitoring_metrics": ["precision", "recall", "drift_KL", "business_KPI"],
    "threshold_definitions": "如何定义阈值与告警规则",
    "replacement_hierarchy": ["primary", "secondary", "fallback_rule_based"]
  }}
}}
""".strip()

        try:
            async with self.sem:
                content = await self._call_deepseek(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.5,
                    max_tokens=2200,
                )
            cleaned = self._clean_json_string(content)
            data = json.loads(cleaned)
            return data
        except Exception as e:
            logger.error(f"系统类论文解析失败: {e}")
            return {"error": f"系统类解析失败: {str(e)}"}

    async def _analyze_survey_paper(
        self,
        paper_title: str,
        paper_abstract: str,
        pdf_content: str,
        user_requirement: str,
    ) -> Dict:
        """综述类论文解析"""
        if not self.api_key:
            return {"error": "API未配置"}

        snippet = self._smart_truncate_pdf(pdf_content, max_len=8000)

        system_prompt = """
你是一位领域综述专家，擅长从 Survey / Review / Roadmap 论文中构建技术知识图谱。
你的任务是提取分类树（taxonomy）、方法对比矩阵以及 open challenges。
""".strip()

        user_prompt = f"""
标题：{paper_title}
摘要：{paper_abstract}
正文片段：
{snippet}

### 输出格式 (严格JSON)
{{
  "taxonomy_tree": {{
    "root": "本综述的领域名称（如 RAG, Agent, LLM Fine-tuning）",
    "children": [
      {{
        "name": "子类名称",
        "subtypes": ["子子类1", "子子类2"]
      }}
    ]
  }},
  "comparison_matrix": [
    {{
      "method_name": "方法/路线名称",
      "pros": ["优点1", "优点2"],
      "cons": ["缺点1", "缺点2"],
      "best_scenario": "最适用的场景"
    }}
  ],
  "open_challenges": [
    "该领域尚未解决的关键问题1",
    "关键问题2"
  ]
}}
""".strip()

        try:
            async with self.sem:
                content = await self._call_deepseek(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.5,
                    max_tokens=2200,
                )
            cleaned = self._clean_json_string(content)
            data = json.loads(cleaned)
            return data
        except Exception as e:
            logger.error(f"综述类论文解析失败: {e}")
            return {"error": f"综述类解析失败: {str(e)}"}

    async def _analyze_benchmark_paper(
        self,
        paper_title: str,
        paper_abstract: str,
        pdf_content: str,
        user_requirement: str,
    ) -> Dict:
        """数据集 / 基准 / Benchmark 论文解析"""
        if not self.api_key:
            return {"error": "API未配置"}

        snippet = self._smart_truncate_pdf(pdf_content, max_len=8000)

        system_prompt = """
你是一位数据集与评测基准设计专家。
你的任务是从 Dataset / Benchmark 论文中提取数据统计特征、构建/清洗/标注流程以及评测指标。
""".strip()

        user_prompt = f"""
标题：{paper_title}
摘要：{paper_abstract}
正文片段：
{snippet}

### 输出格式 (严格JSON)
{{
  "dataset_stats": {{
    "num_samples": "样本数量（如估算值也可以）",
    "num_tokens": "大致 token 数（如果适用）",
    "languages": ["en", "zh", "..."],
    "domains": ["code", "wiki", "forum", "..."]
  }},
  "collection_pipeline": {{
    "sources": ["数据来源1", "数据来源2"],
    "filtering_rules": ["去重规则", "长度/质量过滤"],
    "preprocessing": "其他预处理步骤"
  }},
  "annotation_method": {{
    "type": "human / LLM-assisted / mixed",
    "quality_control": ["双人标注", "仲裁机制", "LLM 一致性检查"]
  }},
  "evaluation_protocol": {{
    "tasks": ["任务1", "任务2"],
    "metrics": ["accuracy", "F1", "Brier score"],
    "leaderboard_rules": "排行榜规则与注意事项"
  }}
}}
""".strip()

        try:
            async with self.sem:
                content = await self._call_deepseek(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.5,
                    max_tokens=2200,
                )
            cleaned = self._clean_json_string(content)
            data = json.loads(cleaned)
            return data
        except Exception as e:
            logger.error(f"Benchmark 类论文解析失败: {e}")
            return {"error": f"Benchmark 类解析失败: {str(e)}"}

    async def _analyze_industry_paper(
        self,
        paper_title: str,
        paper_abstract: str,
        pdf_content: str,
        user_requirement: str,
    ) -> Dict:
        """工业界经验 / Case Study 论文解析"""
        if not self.api_key:
            return {"error": "API未配置"}

        snippet = self._smart_truncate_pdf(pdf_content, max_len=8000)

        system_prompt = """
你是一位大规模生产系统的 Tech Lead。
你的任务是从工业界经验/案例论文中提取：规模量级、踩过的坑、失败的尝试以及成本/性能权衡。
""".strip()

        user_prompt = f"""
标题：{paper_title}
摘要：{paper_abstract}
正文片段：
{snippet}

### 输出格式 (严格JSON)
{{
  "deployment_scale": {{
    "qps": "大致 QPS 或吞吐量级别",
    "num_users": "服务用户规模（如 1e7, 1e9）",
    "regions": ["部署区域/机房分布"]
  }},
  "lessons_learned": [
    "关键经验/教训1（包括失败尝试）",
    "关键经验/教训2"
  ],
  "negative_results": [
    "明确说明某种方案/算法在真实环境下失败的案例",
    "以及失败原因"
  ],
  "operational_costs": {{
    "hardware": "大致机器/GPU 规模",
    "latency_budget": "p99/p999 延迟预算",
    "cost_tradeoffs": "在效果与成本之间做的关键取舍"
  }}
}}
""".strip()

        try:
            async with self.sem:
                content = await self._call_deepseek(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.5,
                    max_tokens=2200,
                )
            cleaned = self._clean_json_string(content)
            data = json.loads(cleaned)
            return data
        except Exception as e:
            logger.error(f"工业类论文解析失败: {e}")
            return {"error": f"工业类解析失败: {str(e)}"}

    async def _analyze_theory_paper(
        self,
        paper_title: str,
        paper_abstract: str,
        pdf_content: str,
        user_requirement: str,
    ) -> Dict:
        """理论/数学类论文解析"""
        if not self.api_key:
            return {"error": "API未配置"}

        snippet = self._smart_truncate_pdf(pdf_content, max_len=8000)

        system_prompt = """
你是一位理论机器学习与优化方向的研究者。
你的任务是从理论/数学类论文中提取：核心定理、关键假设以及对工程实践的启示。
""".strip()

        user_prompt = f"""
标题：{paper_title}
摘要：{paper_abstract}
正文片段：
{snippet}

### 输出格式 (严格JSON)
{{
  "core_theorems": [
    {{
      "name": "定理名称或简要描述",
      "informal_statement": "用大白话解释定理说了什么",
      "formal_statement": "较为形式化的定理表述（如果可以）",
      "conditions": ["关键假设1", "关键假设2"],
      "implications_for_practice": "对学习率/batch size/模型选择等的工程启示"
    }}
  ],
  "assumptions": [
    "数据分布/光滑性/凸性等假设条件列表"
  ]
}}
""".strip()

        try:
            async with self.sem:
                content = await self._call_deepseek(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.4,
                    max_tokens=2200,
                )
            cleaned = self._clean_json_string(content)
            data = json.loads(cleaned)
            return data
        except Exception as e:
            logger.error(f"理论类论文解析失败: {e}")
            return {"error": f"理论类解析失败: {str(e)}"}

    async def analyze_paper_with_router(
        self,
        paper_title: str,
        paper_abstract: str,
        pdf_content: str,
        user_requirement: str,
    ) -> Dict:
        """
        综合入口：先分类，再根据不同体裁走不同 Prompt 策略
        """
        # 先用前 2000 字作为引言片段
        intro_snippet = pdf_content[:2000]
        paper_type = await self.classify_paper_type(
            paper_title,
            paper_abstract,
            intro_snippet,
        )

        logger.info(f"论文体裁识别为: {paper_type}")

        if paper_type == "method":
            analysis = await self._analyze_method_paper(
                paper_title, paper_abstract, pdf_content, user_requirement
            )
        elif paper_type == "system":
            analysis = await self._analyze_system_paper(
                paper_title, paper_abstract, pdf_content, user_requirement
            )
        elif paper_type == "survey":
            analysis = await self._analyze_survey_paper(
                paper_title, paper_abstract, pdf_content, user_requirement
            )
        elif paper_type == "benchmark":
            analysis = await self._analyze_benchmark_paper(
                paper_title, paper_abstract, pdf_content, user_requirement
            )
        elif paper_type == "industry":
            analysis = await self._analyze_industry_paper(
                paper_title, paper_abstract, pdf_content, user_requirement
            )
        elif paper_type == "theory":
            analysis = await self._analyze_theory_paper(
                paper_title, paper_abstract, pdf_content, user_requirement
            )
        else:
            # 回退到通用精读
            analysis = await self.analyze_paper_pdf(
                paper_title, paper_abstract, pdf_content, user_requirement
            )

        return {
            "paper_type": paper_type,
            "analysis": analysis,
        }




    async def generate_implementation_path(self, papers_analysis: List[Dict], user_requirement: str) -> Dict:
        """
        基于多篇论文的精读分析，生成综合实现路径
        
        Args:
            papers_analysis: 多篇论文的分析结果列表，每个元素包含：
                - paper_title: 论文标题
                - paper_abstract: 论文摘要
                - analysis: PDF精读分析结果
            user_requirement: 用户需求
            
        Returns:
            包含实现路径的字典
        """
        if not self.api_key:
            return {"error": "API未配置"}
        
        # 构建论文分析摘要，重点保留工程化分析结果
        papers_summary_list = []
        for idx, paper_data in enumerate(papers_analysis, 1):
            # 移除 raw pdf content 以节省 token，只保留提取出的 analysis
            clean_data = {
                "id": f"Paper_{idx}",
                "title": paper_data.get('paper_title', ''),
                # 这里直接把之前的精读结果完整放进去
                "deep_analysis": paper_data.get("analysis", {}) 
            }
            papers_summary_list.append(json.dumps(clean_data, ensure_ascii=False))
            
        papers_summary_text = "\n\n".join(papers_summary_list)
        
        system_prompt = """
你是一位大厂（如 Google / 字节跳动）的 Tech Lead。
你的任务是基于多篇参考论文，为用户设计一份【工业级】的技术落地架构方案（Technical Design Document, TDD）。
你需要进行技术选型（Trade-off analysis），权衡成本、性能和开发难度，给出一个最可行（MVP）的路径。

你的核心原则是：**需求驱动的工程化（Requirement-Driven Engineering）**。
⚠️ 关键要求：
1. **需求优先**：每个实施阶段必须明确说明"为什么这个阶段对用户需求很重要"、"该阶段完成后用户能获得什么价值"。
2. **需求验证**：每个阶段都要有明确的"验收标准"，说明如何验证该阶段是否满足用户需求。
3. **需求适配**：如果论文的方法与用户需求不完全匹配，必须说明如何调整/适配，而不是盲目复现论文。
4. **Evidence-Based Engineering**：所有技术选型必须基于论文数据，严禁空话。

❌ 严禁生成：
- "我们将使用最先进的模型"、"使用标准的数据清洗流程"这种废话
- 只描述论文方法，不说明如何适配用户需求
- 实施阶段只写"复现论文"，不写"如何服务于用户需求"

✅ 必须具体：
- "基于Paper_1的分析，我们将采用其提出的 'Gated-Attention' 机制，而非标准的 Self-Attention，因为Paper_1指出前者在长文本下显存占用降低了40%，这正好解决了用户需求中提到的'处理长文档时显存不足'的问题。"
- "Phase 1 的目标是验证核心算法在用户场景下的可行性。完成后，用户将能够处理自己的数据格式，并获得初步的效果评估。"

如果论文中没有提到具体技术栈，请明确说明"论文未提及，建议使用通用方案"，而不是假装那是论文里的内容。
""".strip()
        
        user_prompt = f"""
### 业务需求（核心输入）
{user_requirement}

**重要**：所有实施阶段都必须围绕这个需求展开，每个阶段都要说明：
- 该阶段如何服务于用户需求
- 该阶段完成后，用户能获得什么价值
- 如何验证该阶段是否满足用户需求

### 候选技术方案（来自论文分析）
{papers_summary_text}

### 架构设计指令
请按照以下逻辑进行推演：

1. **需求分析与技术选型 (Requirement-Driven Selection)**
   - 首先分析用户需求的核心痛点是什么（如：需要处理长文档、需要实时响应、需要低成本部署等）
   - 然后基于论文分析，选择最适合解决用户痛点的技术方案
   - 必须引用具体论文 ID (如 Paper_1) 的具体参数（如 `model_architecture`, `system_components`）
   - 说明：为什么选 Paper_1 的架构而不是 Paper_2？(引用 `pros`/`cons` 或 `performance_metrics` 进行对比)
   - **关键**：如果论文的方法与用户需求不完全匹配，必须说明如何调整/适配

2. **MVP 实施细节 (Requirement-Driven Implementation)**
   - **数据流**：结合用户需求，描述数据如何通过 Paper 中提到的模块。例如："用户输入的是 [用户需求中的具体数据格式]，需要先转换为 Paper_1 要求的格式 [具体格式]"
   - **关键超参**：直接从分析结果中提取 `key_hyperparameters` (如 LR, Batch Size)，但要根据用户需求调整（如：用户需要快速迭代，则 batch size 可以调小）
   - **需求适配**：如果论文的方法需要调整才能适配用户需求，必须明确说明调整点

3. **关键技术栈**：具体到库的版本（如：LangChain v0.1, PyTorch 2.1, ChromaDB），选择时要考虑用户需求（如：用户需要低成本，则选择轻量级库）

4. **SOP (Standard Operating Procedure)**：给出一份可执行的开发手册。
   - 每个阶段都要说明"为什么这个阶段对用户需求很重要"
   - 每个阶段都要有明确的"验收标准"，说明如何验证该阶段是否满足用户需求
   - 不要只写 "Step 1: 复现代码"
   - 要写 "Step 1: 实现 Paper_1 的 `[具体模块名]`，输入维度应调整为 `[具体Input Spec]`，**目的是验证该模块能否处理用户需求中的 [具体场景]**"
   - 论文有讲述到的执行步骤请详细结合论文内容进行描述，论文没有讲述到但是对于用户需要的工程落地必要的步骤，请详细结合用户需求给出建议。
   - 实现步骤上下要有明确逻辑关系，思路要流畅不要出现断层。

### 输出格式 (严格JSON)
{{
    "architectural_decision": {{
        "selected_methodology": "引用论文的具体方法名，来自哪一篇论文",
        "tradeoff_reasoning": "基于论文数据的对比分析..."
        "reasoning": "为什么选它？（例如：虽然论文B精度高，但论文A推理速度快10倍，更适合工业界）",
        "discarded_methodologies": "哪些方法被弃用了，为什么？"
    }},
    "system_architecture": {{
        "pipeline_description": "文字描述数据流向：Raw Data -> Preprocessing -> Model -> API",
        "tech_stack": ["列出特定的库，如果论文提到了特定的依赖"]
    }},
    "development_roadmap_detailed": [
        {{
            "phase": "Phase 1: [阶段名]",
            "requirement_alignment": "该阶段如何服务于用户需求 [具体说明，如：验证核心算法能否处理用户的实际数据格式]",
            "goals": [
                "目标1：高层次目标，结合用户需求和论文方法 [具体说明，如：验证 Paper_1 的嵌入模块能否处理用户的长文档场景]",
                "目标2：高层次目标，结合用户需求和论文方法 [具体说明，如：建立用户数据格式到论文输入格式的转换流程]"
            ],
            "deliverables": [
                "交付物1：要能直接服务于用户需求 [具体说明，如：能够处理用户实际数据格式的嵌入模块]",
                "交付物2：要能直接服务于用户需求 [具体说明，如：针对用户场景的初步效果评估报告]"
            ],
            "checklist": [
            
                "1.具体执行步骤",
                "2. 具体执行步骤",
                "3. 具体执行步骤",          
                "4. 具体执行步骤",
                "...",
                ],
            "definition_of_done": "验收标准：不仅要达到 Paper_X 的 [具体指标] [具体数值]，还要验证 [用户需求相关的指标，如：能否处理用户的实际数据格式，响应时间是否满足用户要求]"
        }}
    ],
    "risk_mitigation": {{
        "data_scarcity": "如果数据不够怎么办？（如：使用大模型生成合成数据）",
        "performance_issue": "如果推理太慢怎么办？（如：量化为INT8, 使用ONNX Runtime）"
        "gap_analysis": "引用 `implementation_gap` 字段的内容",
        "mitigation": "针对该缺口的解决方案"
    }}
}}
""".strip()
        
        max_retries = 3
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                async with self.sem:
                    content = await self._call_deepseek(
                        [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.7,
                        max_tokens=4000,  # 增加token限制，避免内容被截断
                    )

                cleaned = self._clean_json_string(content)
                print(f"清理后的JSON内容（前500字符）: {cleaned}")
                logger.debug(f"清理后的JSON内容（前500字符）: {cleaned[:500]}")
                
                # 尝试解析JSON
                try:
                    data = json.loads(cleaned)
                except json.JSONDecodeError as json_err:
                    # JSON解析失败，尝试更智能的提取
                    logger.warning(f"直接JSON解析失败，尝试提取JSON块: {json_err}")
                    logger.warning(f"原始内容长度: {len(cleaned)}, 前1000字符: {cleaned[:1000]}")
                    
                    # 尝试提取第一个完整的JSON对象
                    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group())
                            logger.info("成功从文本中提取JSON")
                        except json.JSONDecodeError:
                            raise ValueError(f"提取的JSON块仍然无效: {json_err}")
                    else:
                        raise ValueError(f"无法从响应中找到有效的JSON结构: {json_err}")
                
                logger.info(f"生成实现路径成功（第 {attempt} 次尝试）")
                return data

            except Exception as e:
                last_error = e
                logger.error(f"生成实现路径失败（第 {attempt} 次尝试）: {e}")
                logger.error(f"异常类型: {type(e).__name__}")
                # 记录更多上下文信息
                if hasattr(e, 'pos'):
                    logger.error(f"JSON解析错误位置: {e.pos}")
                if attempt == max_retries:
                    # 最后一次尝试失败时，记录完整内容（截断到2000字符）
                    try:
                        async with self.sem:
                            content = await self._call_deepseek(
                                [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt},
                                ],
                                temperature=0.7,
                                max_tokens=4000,
                            )
                        logger.error(f"最后一次尝试的原始响应（前2000字符）: {content[:2000]}")
                    except:
                        pass

                # 简单退避重试，避免瞬时错误（网络抖动、限流等）
                if attempt < max_retries:
                    await asyncio.sleep(1.0 * attempt)

        # 多次重试仍失败，返回统一错误结构
        return {"error": f"生成失败: {str(last_error) if last_error else '未知错误'}"}

# 单例模式保持不变...
_llm_service = None
def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service