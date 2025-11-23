"""
将数据库中已有的论文索引到向量数据库
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.database import get_db_connection
from services.vector_service import get_vector_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def index_existing_papers():
    """将数据库中所有论文添加到向量数据库"""
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有论文
        cursor.execute("""
            SELECT arxiv_id, title, abstract 
            FROM papers 
            WHERE arxiv_id IS NOT NULL 
            AND title IS NOT NULL
            ORDER BY created_at DESC
        """)
        
        papers = cursor.fetchall()
        conn.close()
        
        logger.info(f"找到 {len(papers)} 篇论文需要索引")
        
        if not papers:
            logger.warning("数据库中没有论文，请先运行爬虫")
            return
        
        # 获取向量服务
        vector_service = get_vector_service()
        
        # 检查向量数据库中已有的论文
        existing_count = vector_service.get_paper_count()
        logger.info(f"向量数据库中已有 {existing_count} 篇论文")
        
        # 处理每篇论文
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for paper in papers:
            try:
                arxiv_id = paper["arxiv_id"]
                title = paper["title"]
                abstract = paper["abstract"] or ""
                
                if not title or not arxiv_id:
                    skipped_count += 1
                    continue
                
                # 检查是否已存在（通过尝试查询）
                try:
                    # 尝试获取，如果不存在会抛出异常或返回空
                    results = vector_service.collection.get(ids=[arxiv_id])
                    if results and results.get('ids') and len(results['ids']) > 0:
                        skipped_count += 1
                        logger.debug(f"论文 {arxiv_id} 已存在于向量数据库，跳过")
                        continue
                except:
                    pass  # 不存在，继续添加
                
                # 添加到向量数据库
                vector_service.add_paper(arxiv_id, title, abstract)
                processed_count += 1
                
                if processed_count % 10 == 0:
                    logger.info(f"已处理 {processed_count} 篇论文...")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"处理论文 {paper.get('arxiv_id', 'unknown')} 失败: {str(e)}")
                continue
        
        logger.info(f"索引完成！")
        logger.info(f"  - 成功处理: {processed_count} 篇")
        logger.info(f"  - 跳过（已存在）: {skipped_count} 篇")
        logger.info(f"  - 处理失败: {error_count} 篇")
        logger.info(f"  - 向量数据库总数: {vector_service.get_paper_count()} 篇")
        
    except Exception as e:
        logger.error(f"索引过程失败: {str(e)}")
        raise

if __name__ == "__main__":
    index_existing_papers()

