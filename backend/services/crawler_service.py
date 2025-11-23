"""
爬虫服务层 - 封装业务逻辑
"""
from fastapi import BackgroundTasks
from datetime import date, timedelta
from typing import Dict, List
import asyncio
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_arxiv_crawl_task(keywords: List[str], background_tasks: BackgroundTasks) -> Dict:
    """
    封装了启动爬虫任务的核心业务逻辑
    """
    # 1. 准备参数 (业务逻辑)
    today = date.today()
    days_ago = today - timedelta(days=30)
    date_from = days_ago.strftime("%Y-%m-%d")
    date_until = today.strftime("%Y-%m-%d")

    # 2. 调度后台任务 (业务逻辑)
    background_tasks.add_task(
        run_crawler,
        keywords=keywords,
        date_from=date_from,
        date_until=date_until
    )

    # 3. 返回结果
    return {"message": "爬虫任务已在后台启动", "keywords": keywords}

async def run_crawler(keywords: List[str], date_from: str, date_until: str):
    """
    实际执行爬虫的后台任务函数
    爬取完成后立即进行向量化处理
    """
    try:
        logger.info(f"开始爬取论文: {keywords}, 时间范围: {date_from} 到 {date_until}")
        
        # 导入爬虫模块
        import sys
        from pathlib import Path
        arxiv_crawler_path = Path(__file__).parent.parent.parent / "arxiv_crawler"
        if str(arxiv_crawler_path) not in sys.path:
            sys.path.insert(0, str(arxiv_crawler_path))
        
        from arxiv_crawler import ArxivScraper
        from services.vector_service import get_vector_service
        from database.database import get_db_connection, save_paper
        import re
        
        # 创建爬虫实例（不翻译，加快速度）
        scraper = ArxivScraper(
            date_from=date_from,
            date_until=date_until,
            optional_keywords=keywords,
            category_whitelist=["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.IR", "cs.MA"],
            trans_to=None  # 不翻译，加快速度
        )
        
        # 执行爬取
        await scraper.fetch_all()
        
        logger.info(f"爬虫任务完成，共爬取 {len(scraper.papers)} 篇论文，开始保存到数据库...")
        
        # 将爬取的论文保存到项目数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        saved_count = 0
        for paper in scraper.papers:
            try:
                # 从URL中提取arxiv_id
                # URL格式: https://arxiv.org/abs/2401.12345 或 https://arxiv.org/abs/cs/0001001
                # 提取最后一个路径段作为arxiv_id
                arxiv_id = paper.url.split('/')[-1]
                if not arxiv_id or arxiv_id == 'abs':
                    logger.warning(f"无法从URL提取arxiv_id: {paper.url}")
                    continue
                
                # 准备论文数据
                paper_data = {
                    'arxiv_id': arxiv_id,
                    'title': paper.title,
                    'authors': paper.authors,
                    'abstract': paper.abstract,
                    'published_date': paper.first_announced_date.strftime('%Y-%m-%d') if paper.first_announced_date else paper.first_submitted_date.strftime('%Y-%m-%d'),
                    'categories': ','.join(paper.categories),
                    'pdf_url': paper.pdf_url
                }
                
                # 保存到数据库
                save_paper(paper_data)
                saved_count += 1
                
            except Exception as e:
                logger.error(f"保存论文失败: {paper.url}, 错误: {str(e)}")
                continue
        
        conn.close()
        logger.info(f"数据库保存完成，共保存 {saved_count} 篇论文")
        
        # 立即进行向量化处理
        logger.info(f"开始向量化处理...")
        vector_service = get_vector_service()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最近爬取的论文（根据时间范围筛选）
        cursor.execute("""
            SELECT arxiv_id, title, abstract 
            FROM papers 
            WHERE published_date >= ? AND published_date <= ?
            ORDER BY published_date DESC
        """, (date_from, date_until))
        
        papers = cursor.fetchall()
        conn.close()
        
        # 将每篇论文添加到向量数据库
        processed_count = 0
        skipped_count = 0
        for paper in papers:
            try:
                arxiv_id = paper["arxiv_id"]
                title = paper["title"]
                abstract = paper["abstract"] or ""
                
                # 检查是否已存在
                try:
                    results = vector_service.collection.get(ids=[arxiv_id])
                    if results and results.get('ids') and len(results['ids']) > 0:
                        skipped_count += 1
                        continue
                except:
                    pass  # 不存在，继续添加
                
                vector_service.add_paper(arxiv_id, title, abstract)
                processed_count += 1
                
                if processed_count % 10 == 0:
                    logger.info(f"已向量化 {processed_count} 篇论文...")
                
            except Exception as e:
                logger.error(f"向量化论文 {paper.get('arxiv_id', 'unknown')} 失败: {str(e)}")
                continue
        
        logger.info(f"向量化处理完成！")
        logger.info(f"  - 新增向量化: {processed_count} 篇")
        logger.info(f"  - 跳过（已存在）: {skipped_count} 篇")
        logger.info(f"  - 向量数据库总数: {vector_service.get_paper_count()} 篇")
        logger.info(f"爬虫任务全部完成: {keywords}")
        
    except Exception as e:
        logger.error(f"爬虫任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

def get_crawler_status() -> Dict:
    """获取爬虫状态（简化版本）"""
    return {
        "status": "ready",
        "message": "爬虫服务就绪"
    }