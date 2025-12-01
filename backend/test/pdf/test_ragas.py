# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragas",
#     "numpy<2.0",
#     "sentence-transformers>=2.3.0",  # 关键：强制升级它
#     "chromadb",
#     "langchain",
#     "openai",
#     "python-dotenv",
#     "torch",  # 向量计算通常需要它
#     "PyPDF2==3.0.1",
# ]
# ///
"""
使用 Ragas 自动生成测试问题并验证检索链路
读取 PDF 文件夹下的论文，为每篇论文生成相关需求，测试检索系统能否找到正确的论文
"""

import sys
import os
from pathlib import Path
import asyncio
import logging
from typing import List, Dict, Optional
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量（支持项目根目录和 backend 目录的 .env）
from dotenv import load_dotenv
root=project_root.parent
for env_path in [
    root / ".env",

]:
    if env_path.exists():
        load_dotenv(env_path)
from database.database import get_db_connection
from services.pdf import get_pdf_service
from services.matching_service import match_papers
from services.llm_service import get_llm_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 尝试导入 Ragas
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from datasets import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    logger.warning("Ragas 未安装，请运行: pip install ragas")


def get_paper_by_arxiv_id(arxiv_id: str) -> Optional[Dict]:
    """从数据库获取论文信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_all_papers_from_db() -> List[Dict]:
    """从数据库获取所有论文"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM papers")
    papers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return papers

def find_pdf_folder() -> Optional[Path]:
    """查找 PDF 文件夹（使用当前脚本所在目录）"""
    pdf_folder = Path(__file__).parent  # 就是 backend/test/pdf
    if pdf_folder.exists() and pdf_folder.is_dir():
        logger.info(f"找到 PDF 文件夹: {pdf_folder}")
        return pdf_folder

    logger.warning("未找到 PDF 文件夹")
    return None



def get_pdf_files(pdf_folder: Path) -> List[Path]:
    """获取 PDF 文件夹下的所有 PDF 文件"""
    pdf_files = list(pdf_folder.glob("*.pdf"))
    logger.info(f"找到 {len(pdf_files)} 个 PDF 文件")
    return pdf_files


def extract_arxiv_id_from_filename(filename: str) -> Optional[str]:
    """从文件名提取 arxiv_id"""
    # 尝试从文件名提取，例如: "2401.12345.pdf" 或 "arxiv_2401.12345.pdf"
    name = Path(filename).stem
    # 移除 "arxiv_" 前缀（如果有）
    if name.startswith("arxiv_"):
        name = name[6:]
    
    # 去掉 arXiv 版本号后缀（例如 2510.27640v1 -> 2510.27640）
    # 只在末尾是 v+数字 的情况下处理，避免误伤正常文件名
    if "v" in name:
        base, suffix = name.rsplit("v", 1)
        if suffix.isdigit() and base:
            name = base
    
    # 检查是否符合 arxiv_id 格式（例如: 2401.12345 或 cs/0001001）
    if '.' in name or '/' in name:
        return name
    return None


async def generate_question_from_pdf_content(
    pdf_content: str,
    paper_title: str,
    paper_abstract: str,
    llm_service
) -> str:
    """
    使用 LLM 根据 PDF 内容生成相关需求问题
    这个问题应该能够通过检索系统找到这篇论文
    """
    prompt = f"""
你是一个科研需求分析师。请根据以下论文内容，生成一个用户可能提出的"业务需求"或"研究需求"。

论文标题: {paper_title}
论文摘要: {paper_abstract}
论文内容片段（前2000字）: {pdf_content[:2000]}

要求：
1. 生成的需求应该与论文内容高度相关
2. 需求应该用自然语言描述，就像真实用户会提出的问题一样
3. 需求可以是业务场景（如"我需要做一个工业质检系统"）或研究问题（如"如何提高图像识别的准确率"）
4. 需求应该能够通过检索系统找到这篇论文

只返回需求文本，不要返回其他内容。
"""
    
    try:
        # 使用 LLM 服务的内部方法（通过反射访问）
        if hasattr(llm_service, '_call_deepseek'):
            response = await llm_service._call_deepseek(
                [{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
                force_json=False
            )
            return response.strip()
        else:
            # 如果方法不可用，使用简单的基于标题和摘要的问题生成
            logger.warning("无法使用 LLM 生成问题，使用基于标题的简单问题")
            return f"我需要研究关于 {paper_title} 的相关技术"
    except Exception as e:
        logger.error(f"生成问题失败: {e}")
        # 如果生成失败，使用基于标题和摘要的简单问题
        return f"我需要研究关于 {paper_title} 的相关技术"


async def process_pdf_file(
    pdf_path: Path,
    pdf_service,
    llm_service,
    pdf_folder: Path
) -> Optional[Dict]:
    """处理单个 PDF 文件"""
    try:
        # 从文件名提取 arxiv_id
        arxiv_id = extract_arxiv_id_from_filename(pdf_path.name)
        
        if not arxiv_id:
            logger.warning(f"无法从文件名提取 arxiv_id: {pdf_path.name}")
            # 尝试从数据库查找匹配的论文
            # 这里可以根据文件大小、修改时间等匹配，但为了简化，我们跳过
            return None
        
        logger.info(f"处理 PDF: {pdf_path.name}, arxiv_id: {arxiv_id}")
        
        # 从数据库获取论文信息
        paper_info = get_paper_by_arxiv_id(arxiv_id)
        
        if not paper_info:
            logger.warning(f"数据库中未找到论文: {arxiv_id}")
            return None
        
        # 提取 PDF 文本内容
        pdf_content = pdf_service.extract_text_from_pdf(pdf_path, max_pages=10)
        
        if not pdf_content or len(pdf_content) < 100:
            logger.warning(f"PDF 内容提取失败或内容过少: {arxiv_id}")
            return None
        
        # 生成测试问题
        question = await generate_question_from_pdf_content(
            pdf_content,
            paper_info.get('title', ''),
            paper_info.get('abstract', ''),
            llm_service
        )
        
        return {
            'arxiv_id': arxiv_id,
            'paper_info': paper_info,
            'question': question,
            'pdf_content': pdf_content[:1000],  # 只保存前1000字用于测试
        }
        
    except Exception as e:
        logger.error(f"处理 PDF 文件失败 {pdf_path}: {e}")
        return None


async def test_retrieval(
    question: str,
    expected_arxiv_id: str,
    top_k: int = 10
) -> Dict:
    """
    测试检索链路
    返回检索结果和评估指标
    """
    try:
        # 调用检索系统
        results = await match_papers(question, top_k=top_k)
        
        # 检查期望的论文是否在结果中
        found = False
        rank = -1
        score = 0
        
        for idx, result in enumerate(results):
            if result.get('paper_id') == expected_arxiv_id:
                found = True
                rank = idx + 1
                score = result.get('score', 0)
                break
        
        return {
            'question': question,
            'expected_arxiv_id': expected_arxiv_id,
            'found': found,
            'rank': rank,
            'score': score,
            'total_results': len(results),
            'top_3_papers': [
                {
                    'paper_id': r.get('paper_id'),
                    'title': r.get('title', '')[:50],
                    'score': r.get('score', 0)
                }
                for r in results[:3]
            ]
        }
    except Exception as e:
        logger.error(f"检索测试失败: {e}")
        return {
            'question': question,
            'expected_arxiv_id': expected_arxiv_id,
            'found': False,
            'error': str(e)
        }


async def evaluate_with_ragas(
    test_cases: List[Dict]
) -> Dict:
    """
    使用 Ragas 评估检索质量，底层 LLM 使用 DeepSeek（通过 OpenAI 兼容接口）
    """
    if not RAGAS_AVAILABLE:
        logger.warning("Ragas 未安装，跳过 Ragas 评估")
        return {}
    
    try:
        # 使用 DeepSeek 作为 OpenAI 兼容接口
        import os
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_key:
            logger.warning("未配置 DEEPSEEK_API_KEY，跳过 Ragas 评估")
            return {}
        
        # 通过环境变量把 DeepSeek 暴露为 OpenAI 兼容接口
        # Ragas 内部会使用 openai 库读取这些变量
        os.environ["OPENAI_API_KEY"] = deepseek_key
        # DeepSeek 的 OpenAI 兼容 base_url，一般为 /v1 前缀
        os.environ.setdefault("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        
        # 准备数据集
        dataset_dict = {
            'question': [],
            'contexts': [],
            'answer': [],
            'ground_truth': []
        }
        
        for test_case in test_cases:
            question = test_case['question']
            expected_paper = test_case['paper_info']
            
            # 构建上下文（论文的标题和摘要）
            context = f"标题: {expected_paper.get('title', '')}\n摘要: {expected_paper.get('abstract', '')}"
            
            # 构建答案（期望的论文ID）
            answer = expected_paper.get('arxiv_id', '')
            
            # 构建 ground truth（期望的论文信息）
            ground_truth = f"论文ID: {answer}, 标题: {expected_paper.get('title', '')}"
            
            dataset_dict['question'].append(question)
            dataset_dict['contexts'].append([context])
            dataset_dict['answer'].append(answer)
            dataset_dict['ground_truth'].append(ground_truth)
        
        # 创建数据集
        dataset = Dataset.from_dict(dataset_dict)
        
        # 运行评估
        result = evaluate(
            dataset=dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ]
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ragas 评估失败: {e}")
        return {}


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始 Ragas 测试流程")
    logger.info("=" * 60)
    
    # 1. 查找 PDF 文件夹
    pdf_folder = find_pdf_folder()
    
    if not pdf_folder:
        logger.error("未找到 PDF 文件夹")
        return
    
    # 2. 获取所有 PDF 文件
    pdf_files = get_pdf_files(pdf_folder)
    
    if not pdf_files:
        logger.warning(f"PDF 文件夹中没有找到 PDF 文件: {pdf_folder}")
        logger.info("请将论文 PDF 文件放入该文件夹")
        return
    
    # 3. 初始化服务
    pdf_service = get_pdf_service()
    llm_service = get_llm_service()
    
    # 4. 处理每个 PDF 文件
    test_cases = []
    logger.info(f"开始处理 {len(pdf_files)} 个 PDF 文件...")
    
    for pdf_file in pdf_files:
        test_case = await process_pdf_file(pdf_file, pdf_service, llm_service, pdf_folder)
        if test_case:
            test_cases.append(test_case)
            logger.info(f"✓ 已处理: {test_case['arxiv_id']}")
    
    if not test_cases:
        logger.error("没有成功处理任何 PDF 文件")
        return
    
    logger.info(f"成功处理 {len(test_cases)} 个测试用例")
    
    # 5. 测试检索链路
    logger.info("=" * 60)
    logger.info("开始测试检索链路...")
    logger.info("=" * 60)
    
    retrieval_results = []
    for test_case in test_cases:
        logger.info(f"测试问题: {test_case['question'][:50]}...")
        result = await test_retrieval(
            test_case['question'],
            test_case['arxiv_id'],
            top_k=10
        )
        retrieval_results.append(result)
        
        if result['found']:
            logger.info(f"  ✓ 找到期望论文，排名: {result['rank']}, 分数: {result['score']}")
        else:
            logger.warning(f"  ✗ 未找到期望论文")
            logger.info(f"  前3个结果: {[p['paper_id'] for p in result.get('top_3_papers', [])]}")
    
    # 6. 统计结果
    logger.info("=" * 60)
    logger.info("检索测试结果统计")
    logger.info("=" * 60)
    
    found_count = sum(1 for r in retrieval_results if r['found'])
    total_count = len(retrieval_results)
    success_rate = (found_count / total_count * 100) if total_count > 0 else 0
    
    logger.info(f"总测试用例数: {total_count}")
    logger.info(f"成功找到期望论文: {found_count}")
    logger.info(f"成功率: {success_rate:.2f}%")
    
    # 计算平均排名（只统计找到的）
    found_results = [r for r in retrieval_results if r['found']]
    if found_results:
        avg_rank = sum(r['rank'] for r in found_results) / len(found_results)
        avg_score = sum(r['score'] for r in found_results) / len(found_results)
        logger.info(f"平均排名: {avg_rank:.2f}")
        logger.info(f"平均分数: {avg_score:.2f}")
    
    # 7. 使用 Ragas 评估（如果可用）
    if RAGAS_AVAILABLE:
        logger.info("=" * 60)
        logger.info("开始 Ragas 评估...")
        logger.info("=" * 60)
        
        ragas_results = await evaluate_with_ragas(test_cases)
        if ragas_results:
            logger.info("Ragas 评估完成")
            logger.info(f"评估结果: {ragas_results}")
    
    # 8. 保存结果到文件
    output_file = project_root  / "test" / "pdf" / "ragas_test_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        'test_cases': [
            {
                'arxiv_id': tc['arxiv_id'],
                'question': tc['question'],
                'paper_title': tc['paper_info'].get('title', ''),
            }
            for tc in test_cases
        ],
        'retrieval_results': retrieval_results,
        'statistics': {
            'total_count': total_count,
            'found_count': found_count,
            'success_rate': success_rate,
            'avg_rank': avg_rank if found_results else None,
            'avg_score': avg_score if found_results else None,
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"测试结果已保存到: {output_file}")
    logger.info("=" * 60)
    logger.info("测试完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

