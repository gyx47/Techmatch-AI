"""
LLM 服务 - 使用 DeepSeek API 进行论文评分
"""
import logging
import os
import json
from typing import Dict, List
import httpx

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        """初始化 LLM 服务"""
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.api_base = "https://api.deepseek.com/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("未设置 DEEPSEEK_API_KEY，LLM 评分功能将不可用")
    
    async def score_paper(self, user_requirement: str, paper_title: str, paper_abstract: str) -> Dict:
        """
        使用 DeepSeek 对单篇论文进行评分
        返回: {"score": float, "reason": str}
        """
        if not self.api_key:
            return {
                "score": 0.5,
                "reason": "LLM API 未配置，返回默认分数"
            }
        
        try:
            # 构建提示词
            prompt = f"""你是一位技术专家，需要评估一篇学术论文是否匹配企业的技术需求。

企业需求：
{user_requirement}

论文信息：
标题：{paper_title}
摘要：{paper_abstract}

请仔细分析这篇论文是否能够解决或部分解决企业的技术需求。请从以下维度评估：
1. 技术相关性（论文的技术方向是否与企业需求匹配）
2. 解决方案可行性（论文提出的方法是否可以直接或间接应用于企业场景）
3. 创新性和先进性（论文的技术是否具有创新性和先进性）

请以 JSON 格式返回结果，格式如下：
{{
    "score": 0.0-1.0之间的浮点数（1.0表示完全匹配，0.0表示完全不匹配）,
    "reason": "详细的匹配理由，说明为什么给出这个分数，包括论文的优势和可能的局限性"
}}

只返回 JSON，不要其他文字。"""

            # 调用 DeepSeek API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_base,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "你是一位专业的技术评估专家。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 500
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                # 提取回复内容
                content = result["choices"][0]["message"]["content"].strip()
                
                # 尝试解析 JSON（可能包含 markdown 代码块）
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # 解析 JSON
                score_data = json.loads(content)
                
                # 确保分数在 0-1 之间
                score = max(0.0, min(1.0, float(score_data.get("score", 0.5))))
                reason = score_data.get("reason", "未提供理由")
                
                return {
                    "score": score,
                    "reason": reason
                }
                
        except Exception as e:
            logger.error(f"LLM 评分失败: {str(e)}")
            return {
                "score": 0.5,
                "reason": f"评分过程出错: {str(e)}"
            }
    
    async def score_papers_batch(
        self, 
        user_requirement: str, 
        papers: List[Dict]
    ) -> List[Dict]:
        """
        批量评分论文（逐一调用，避免并发过多）
        papers: [{"paper_id": str, "title": str, "abstract": str}, ...]
        返回: [{"paper_id": str, "score": float, "reason": str}, ...]
        """
        results = []
        
        for i, paper in enumerate(papers):
            logger.info(f"正在评分论文 {i+1}/{len(papers)}: {paper['paper_id']}")
            
            score_result = await self.score_paper(
                user_requirement,
                paper["title"],
                paper["abstract"]
            )
            
            results.append({
                "paper_id": paper["paper_id"],
                "score": score_result["score"],
                "reason": score_result["reason"]
            })
        
        # 按分数排序（从高到低）
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results

# 全局单例
_llm_service = None

def get_llm_service() -> LLMService:
    """获取 LLM 服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

