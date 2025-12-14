import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_llm_service():
    print("=" * 60)
    print("调试 LLM 服务状态")
    print("=" * 60)
    
    # 1. 检查环境变量
    print("\n1. 环境变量检查:")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    print(f"   DEEPSEEK_API_KEY: {'已设置' if api_key else '未设置'}")
    if api_key:
        print(f"   长度: {len(api_key)}")
        print(f"   内容: {api_key[:15]}...{api_key[-10:] if len(api_key) > 25 else ''}")
    
    # 2. 测试单例获取
    print("\n2. 测试获取 LLM 服务实例:")
    try:
        from services.llm_service import get_llm_service
        llm_service = get_llm_service()
        print(f"   ✅ 成功获取 LLMService 实例")
        print(f"   API Key 属性: {'已设置' if llm_service.api_key else '未设置'}")
        print(f"   长度: {len(llm_service.api_key)}")
        print(f"   API Base: {llm_service.api_base}")
        
        # 3. 测试 score_requirements_for_paper 方法
        print("\n3. 测试 score_requirements_for_paper 方法:")
        import asyncio
        
        # 创建模拟的需求数据
        mock_requirements = [
            {
                "requirement_id": "REQ001",
                "title": "测试需求",
                "industry": "人工智能",
                "technical_level": "中",
                "market_size": "中型",
                "pain_points": "数据处理能力不足",
                "vector_score": 0.75  # 添加向量分数
            }
        ]
        
        async def test():
            try:
                results = await llm_service.score_requirements_for_paper(
                    paper_title="测试论文",
                    paper_abstract="这是论文摘要",
                    paper_categories="AI,ML",
                    requirements=mock_requirements
                )
                print(f"   ✅ 方法调用成功")
                print(f"   返回结果数量: {len(results)}")
                if results:
                    result = results[0]
                    print(f"   分数: {result.get('score')}")
                    print(f"   理由: {result.get('reason')}")
                    print(f"   建议: {result.get('implementation_suggestion')}")
                    print(f"   匹配类型: {result.get('match_type')}")
            except Exception as e:
                print(f"   ❌ 方法调用失败: {type(e).__name__}: {e}")
        
        asyncio.run(test())
        
    except Exception as e:
        print(f"   ❌ 获取失败: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    debug_llm_service()