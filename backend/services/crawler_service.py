"""
爬虫服务层 - 封装业务逻辑
"""
from fastapi import BackgroundTasks
from datetime import date, timedelta
from typing import Dict, List
import asyncio
import logging
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局爬虫状态管理
_crawler_running = False
_crawler_should_stop = False
_crawler_task = None

def start_arxiv_crawl_task(keywords: List[str], background_tasks: BackgroundTasks, days: int = 30) -> Dict:
    """
    封装了启动爬虫任务的核心业务逻辑
    
    Args:
        keywords: 关键词列表
        days: 爬取最近多少天的论文，默认30天，范围1-365
        background_tasks: FastAPI后台任务
    """
    global _crawler_running, _crawler_should_stop
    
    # 如果已有爬虫在运行，返回错误
    if _crawler_running:
        return {
            "message": "爬虫已在运行中，请先停止当前任务",
            "status": "running"
        }
    
    # 重置停止标志
    _crawler_should_stop = False
    
    # 限制天数范围，避免过大或过小
    days = max(1, min(365, days))
    
    # 1. 准备参数 (业务逻辑)
    today = date.today()
    days_ago = today - timedelta(days=days)
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
    return {
        "message": "爬虫任务已在后台启动",
        "keywords": keywords,
        "days": days,
        "date_from": date_from,
        "date_until": date_until,
        "status": "started"
    }

async def run_crawler(keywords: List[str], date_from: str, date_until: str):
    """
    实际执行爬虫的后台任务函数
    爬取完成后立即进行向量化处理
    """
    global _crawler_running, _crawler_should_stop
    
    _crawler_running = True
    _crawler_should_stop = False
    
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
        
        # 设置停止标志检查函数
        def should_stop():
            return _crawler_should_stop
        
        scraper.should_stop = should_stop
        
        # 创建一个假的PaperDatabase类，避免保存到arxiv_crawler的数据库
        class FakePaperDatabase:
            def add_papers(self, papers):
                # 什么都不做，只是为了避免process_papers()报错
                pass
        
        # 临时替换paper_db，避免保存到arxiv_crawler的数据库
        original_paper_db = scraper.paper_db
        scraper.paper_db = FakePaperDatabase()
        
        # 执行爬取（process_papers会调用paper_db.add_papers，但我们的假类不会真正保存）
        await scraper.fetch_all()
        
        # 恢复paper_db引用（虽然已经处理完了，但为了安全）
        scraper.paper_db = original_paper_db
        
        # 检查是否有论文
        if len(scraper.papers) == 0:
            logger.warning(f"未找到匹配的论文")
            logger.warning(f"可能的原因：")
            logger.warning(f"  1. 日期范围 {date_from} 到 {date_until} 内没有符合条件的论文")
            logger.warning(f"  2. 关键词 {keywords} 可能太严格")
            logger.warning(f"  3. 领域白名单可能过滤掉了所有论文")
            return  # 提前返回，不执行后续的保存和向量化
        
        logger.info(f"爬虫任务完成，共爬取 {len(scraper.papers)} 篇论文，开始保存到项目数据库...")
        
        # 将爬取的论文保存到项目数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        saved_count = 0
        skipped_count = 0
        for paper in scraper.papers:
            # 检查是否应该停止
            if _crawler_should_stop:
                logger.info(f"收到停止请求，已保存 {saved_count} 篇新论文，跳过 {skipped_count} 篇已存在论文，停止保存")
                break
            
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
                
                # 保存到数据库（如果已存在会返回已存在的ID，不会重复插入）
                paper_id, is_new = save_paper(paper_data)
                if paper_id:
                    if is_new:
                        saved_count += 1
                    else:
                        skipped_count += 1
                else:
                    logger.warning(f"保存论文失败: {arxiv_id}")
                
            except Exception as e:
                logger.error(f"保存论文失败: {paper.url}, 错误: {str(e)}")
                continue
        
        conn.close()
        logger.info(f"数据库保存完成，共保存 {saved_count} 篇新论文，跳过 {skipped_count} 篇已存在论文")
        
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
        error_count = 0
        model_load_failed = False
        
        for paper in papers:
            # 检查是否应该停止
            if _crawler_should_stop:
                logger.info(f"收到停止请求，已向量化 {processed_count} 篇论文，停止向量化")
                break
            
            try:
                arxiv_id = paper["arxiv_id"]
                title = paper["title"]
                abstract = paper["abstract"] or ""
                
                # 检查是否已存在并添加（add_paper 内部会检查）
                added = vector_service.add_paper(arxiv_id, title, abstract)
                if added:
                    processed_count += 1
                else:
                    skipped_count += 1
                
                if processed_count % 10 == 0:
                    logger.info(f"已向量化 {processed_count} 篇论文...")
                
            except RuntimeError as e:
                # 如果是模型加载失败，只记录一次，然后跳过所有后续论文
                if not model_load_failed and ('DLL load failed' in str(e) or 'tensorflow' in str(e).lower() or '向量模型加载失败' in str(e)):
                    model_load_failed = True
                    logger.error("=" * 60)
                    logger.error("向量模型加载失败，无法继续向量化处理")
                    logger.error("错误信息: " + str(e))
                    logger.error("")
                    logger.error("解决方案：")
                    logger.error("  1. 重新安装 tensorflow: pip install --upgrade tensorflow")
                    logger.error("  2. 或者安装 CPU 版本: pip install tensorflow-cpu")
                    logger.error("  3. 或者使用 conda 安装: conda install tensorflow")
                    logger.error("  4. 检查是否安装了 Visual C++ Redistributable")
                    logger.error("  5. 或者使用其他向量化方案（如 OpenAI embeddings）")
                    logger.error("=" * 60)
                    logger.warning("跳过向量化步骤，已保存的论文可以在修复环境后手动索引")
                    break  # 模型加载失败，无法继续
                error_count += 1
                try:
                    paper_id = paper["arxiv_id"] if "arxiv_id" in paper.keys() else "unknown"
                except:
                    paper_id = "unknown"
                logger.error(f"向量化论文 {paper_id} 失败: {str(e)[:200]}")
                continue
            except Exception as e:
                error_count += 1
                # sqlite3.Row 对象使用字典访问方式
                try:
                    paper_id = paper["arxiv_id"] if "arxiv_id" in paper.keys() else "unknown"
                except:
                    paper_id = "unknown"
                logger.error(f"向量化论文 {paper_id} 失败: {str(e)[:200]}")
                continue
        
        if model_load_failed:
            logger.warning(f"向量化处理中断（模型加载失败）")
            logger.warning(f"  - 已保存到数据库: {saved_count} 篇")
            logger.warning(f"  - 已向量化: {processed_count} 篇")
            logger.warning(f"  - 跳过（已存在）: {skipped_count} 篇")
            logger.warning(f"  - 错误: {error_count} 篇")
            logger.warning(f"  - 向量数据库总数: {vector_service.get_paper_count()} 篇")
            logger.warning(f"提示：修复环境后可以使用 /api/matching/index-papers 接口索引剩余论文")
        else:
            logger.info(f"向量化处理完成！")
            logger.info(f"  - 新增向量化: {processed_count} 篇")
            logger.info(f"  - 跳过（已存在）: {skipped_count} 篇")
            logger.info(f"  - 错误: {error_count} 篇")
            logger.info(f"  - 向量数据库总数: {vector_service.get_paper_count()} 篇")
        
        logger.info(f"爬虫任务完成: {keywords}")
        
    except Exception as e:
        logger.error(f"爬虫任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        _crawler_running = False
        _crawler_should_stop = False

def stop_crawler() -> Dict:
    """停止正在运行的爬虫"""
    global _crawler_running, _crawler_should_stop
    
    if not _crawler_running:
        return {
            "status": "not_running",
            "message": "没有正在运行的爬虫任务"
        }
    
    _crawler_should_stop = True
    logger.info("收到停止爬虫请求")
    return {
        "status": "stopping",
        "message": "正在停止爬虫任务，请稍候..."
    }

def get_crawler_status() -> Dict:
    """获取爬虫状态"""
    global _crawler_running, _crawler_should_stop
    
    if _crawler_running:
        if _crawler_should_stop:
            return {
                "status": "stopping",
                "message": "爬虫正在停止中..."
            }
        else:
            return {
                "status": "running",
                "message": "爬虫正在运行中"
            }
    else:
        return {
            "status": "ready",
            "message": "爬虫服务就绪"
        }