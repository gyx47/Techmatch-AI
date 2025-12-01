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
        你是一位精通人工智能领域的首席架构师。用户的输入是企业侧的“业务痛点”。
        请你将其转化为学术界可能用于解决该问题的“具体技术路线”和“专业术语”。

        用户需求："{user_requirement}"

        请遵循以下步骤思考：
        1. 分析痛点：用户到底想要什么？（例如：降本、提速、长文本、多模态）
        2. **枚举技术路径（关键）**：列出 3-5 种能解决该问题的**不同技术流派**。不要只给通用的词（如 "Efficient"），要给具体的方案（如 "Quantization", "Speculative Decoding", "Knowledge Distillation", "Linear Attention", "SNN", "Non-autoregressive" 等）。
        3. 构造增强查询：将这些具体的术语组合成一段文本。

        请严格按照以下格式返回（不要包含 Markdown 格式，不要换行，直接返回一段纯文本）：
        [Keywords]: <技术术语1>, <技术术语2>, <技术术语3>, <技术术语4>, <技术术语5>. [Context]: <一段包含上述技术术语的学术综述风格的描述，涵盖多种可能的技术解决方案>

        示例输入："我想让大模型在手机上跑得快一点"
        示例返回：[Keywords]: Model Quantization, Knowledge Distillation, Edge Computing, MobileNets, Sparse Attention. [Context]: Research on deploying Large Language Models on edge devices focuses on reducing memory footprint and latency. Key approaches include post-training quantization (PTQ) to low-bit precision, structured pruning to enforce sparsity, and architectural innovations like linear attention mechanisms or state-space models (SSMs) to reduce computational complexity.
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
        if not self.api_key:
            return {"error": "API未配置"}

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
            logger.error(f"方法类论文解析失败: {e}")
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
        papers_summary = ""
        for idx, paper_data in enumerate(papers_analysis, 1):
            analysis = paper_data.get("analysis", {})
            eng = analysis.get("engineering_analysis", {}) or analysis
            papers_summary += f"""
[论文 {idx}]
标题：{paper_data.get('paper_title', '')}
模型结构：{eng.get('model_architecture', '')}
输入规格：{eng.get('input_spec', '')}
Loss / 关键超参：{eng.get('loss_function', '')} | {', '.join(eng.get('key_hyperparameters', []))}
实现缺口：{analysis.get('implementation_gap', '')}
复现难度：{analysis.get('reproducibility_score', '')}
---
"""
        
        system_prompt = """
你是一位大厂（如 Google / 字节跳动）的 Tech Lead。
你的任务是基于多篇参考论文，为用户设计一份【工业级】的技术落地架构方案（Technical Design Document, TDD）。
你需要进行技术选型（Trade-off analysis），权衡成本、性能和开发难度，给出一个最可行（MVP）的路径，而不是简单的论文堆砌。
""".strip()
        
        user_prompt = f"""
### 业务需求
{user_requirement}

### 候选技术方案（来自论文分析）
{papers_summary}

### 架构设计指令
请按照以下逻辑进行推演：
1. **技术选型辩论**：对比几篇论文的方法，针对用户的需求，指出哪篇论文的方法最适合作为 Base model？为什么？（Trade-off Analysis）
2. **MVP架构设计**：设计一个最小可行性产品（MVP）的系统架构。包含：数据层、模型层、服务层。
3. **关键技术栈**：具体到库的版本（如：LangChain v0.1, PyTorch 2.1, ChromaDB）。
4. **SOP (Standard Operating Procedure)**：给出一份可执行的开发手册。

### 输出格式 (严格JSON)
{{
    "architectural_decision": {{
        "chosen_baseline_paper": "被选中的核心参考论文",
        "reasoning": "为什么选它？（例如：虽然论文B精度高，但论文A推理速度快10倍，更适合工业界）",
        "discarded_papers": "哪些论文的方法被弃用了，为什么？"
    }},
    "system_architecture": {{
        "pipeline_description": "文字描述数据流向：Raw Data -> Preprocessing -> Model -> API",
        "tech_stack": ["Python 3.10", "FastAPI", "Redis", "Celery", "PyTorch"]
    }},
    "development_roadmap_detailed": [
        {{
            "phase": "Phase 1: Baseline复现",
            "days_estimated": 5,
            "checklist": [
                "Step 1: 跑通论文A的开源代码 demo.py",
                "Step 2: 替换DataLoader为用户私有数据",
                "Step 3: 验证Loss是否下降"
            ],
            "definition_of_done": "模型在测试集上F1 Score > 0.7"
        }}
    ],
    "risk_mitigation": {{
        "data_scarcity": "如果数据不够怎么办？（如：使用大模型生成合成数据）",
        "performance_issue": "如果推理太慢怎么办？（如：量化为INT8, 使用ONNX Runtime）"
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
                    temperature=0.7,
                    max_tokens=3000,
                )

            cleaned = self._clean_json_string(content)
            data = json.loads(cleaned)
            return data
            
        except Exception as e:
            logger.error(f"生成实现路径失败: {e}")
            return {"error": f"生成失败: {str(e)}"}

# 单例模式保持不变...
_llm_service = None
def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service