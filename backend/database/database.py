"""
数据库配置和初始化
"""
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库文件路径
DB_PATH = Path(__file__).parent / "app.db"

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
    return conn

def init_db():
    """初始化数据库表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'researcher',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 如果表已存在但没有 role 字段，添加该字段
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'researcher'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # 字段已存在，忽略错误
        
        # 创建论文表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id VARCHAR(20) UNIQUE NOT NULL,
                title TEXT NOT NULL,
                authors TEXT NOT NULL,
                abstract TEXT,
                published_date DATE,
                categories TEXT,
                pdf_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建搜索历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT NOT NULL,
                results_count INTEGER,
                search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # 创建AI对话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id VARCHAR(100),
                user_message TEXT NOT NULL,
                ai_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # 创建匹配历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                search_desc TEXT NOT NULL,
                match_mode VARCHAR(20),
                result_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # 创建匹配结果表（保存每次匹配的详细结果）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                history_id INTEGER NOT NULL,
                paper_id VARCHAR(20),
                title TEXT,
                abstract TEXT,
                authors TEXT,
                categories TEXT,
                pdf_url TEXT,
                published_date DATE,
                score INTEGER,
                reason TEXT,
                match_type VARCHAR(50),
                vector_score REAL,
                result_order INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (history_id) REFERENCES match_history (id) ON DELETE CASCADE
            )
        """)
        
        # 创建论文解析内容缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_content_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id VARCHAR(20) NOT NULL,
                pdf_url TEXT NOT NULL,
                content TEXT NOT NULL,
                max_pages INTEGER DEFAULT 20,
                use_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(arxiv_id, max_pages)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化成功")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

def get_user_by_username(username: str) -> Optional[dict]:
    """根据用户名获取用户信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_email(email: str) -> Optional[dict]:
    """根据邮箱获取用户信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(username: str, email: str, password_hash: str, role: str = 'researcher') -> int:
    """创建新用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (username, email, password_hash, role)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def save_paper(paper_data: dict) -> Tuple[Optional[int], bool]:
    """
    保存论文信息
    如果论文已存在（根据 arxiv_id），则返回已存在的记录ID，不进行插入或替换
    返回: (论文ID, 是否为新插入)
        - 如果已存在: (paper_id, False)
        - 如果新插入: (paper_id, True)
        - 如果失败: (None, False)
    """
    arxiv_id = paper_data.get('arxiv_id')
    if not arxiv_id:
        logger.warning("论文数据缺少 arxiv_id，无法保存")
        return None, False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 先检查是否已存在
    cursor.execute("SELECT id FROM papers WHERE arxiv_id = ?", (arxiv_id,))
    existing = cursor.fetchone()
    
    if existing:
        # 论文已存在，返回已存在的ID，不进行任何操作
        paper_id = existing['id']
        conn.close()
        return paper_id, False
    
    # 论文不存在，执行插入
    cursor.execute("""
        INSERT INTO papers 
        (arxiv_id, title, authors, abstract, published_date, categories, pdf_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        arxiv_id,
        paper_data.get('title'),
        paper_data.get('authors'),
        paper_data.get('abstract'),
        paper_data.get('published_date'),
        paper_data.get('categories'),
        paper_data.get('pdf_url')
    ))
    paper_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return paper_id, True

def get_papers_by_query(query: str, limit: int = 20) -> list:
    """根据查询条件搜索论文"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM papers 
        WHERE title LIKE ? OR abstract LIKE ? OR authors LIKE ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
    papers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return papers

def save_match_history(user_id: Optional[int], search_desc: str, match_mode: str, results: List[dict]) -> int:
    """
    保存匹配历史
    返回: 匹配历史ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 插入匹配历史记录
        cursor.execute("""
            INSERT INTO match_history (user_id, search_desc, match_mode, result_count)
            VALUES (?, ?, ?, ?)
        """, (user_id, search_desc, match_mode, len(results)))
        
        history_id = cursor.lastrowid
        
        # 插入匹配结果详情
        for order, result in enumerate(results, 1):
            cursor.execute("""
                INSERT INTO match_results (
                    history_id, paper_id, title, abstract, authors, categories,
                    pdf_url, published_date, score, reason, match_type, vector_score, result_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                history_id,
                result.get('paper_id'),
                result.get('title'),
                result.get('abstract'),
                result.get('authors'),
                result.get('categories'),
                result.get('pdf_url'),
                result.get('published_date'),
                result.get('score'),
                result.get('reason'),
                result.get('match_type'),
                result.get('vector_score'),
                order
            ))
        
        conn.commit()
        return history_id
    except Exception as e:
        conn.rollback()
        logger.error(f"保存匹配历史失败: {e}")
        raise
    finally:
        conn.close()

def get_match_history(user_id: Optional[int], page: int = 1, page_size: int = 20) -> dict:
    """
    获取匹配历史列表
    返回: {"total": int, "items": List[dict]}
    注意：如果 user_id 为 None，返回空列表（不允许查看所有用户的历史）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 如果 user_id 为 None，返回空列表（安全考虑）
    if user_id is None:
        conn.close()
        return {
            "total": 0,
            "page": page,
            "page_size": page_size,
            "items": []
        }
    
    # 计算总数
    cursor.execute("SELECT COUNT(*) as total FROM match_history WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * page_size
    cursor.execute("""
        SELECT * FROM match_history 
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (user_id, page_size, offset))
    
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }

def get_match_results_by_history_id(history_id: int) -> List[dict]:
    """
    根据历史ID获取匹配结果详情
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM match_results 
        WHERE history_id = ?
        ORDER BY result_order ASC
    """, (history_id,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_paper_content_cache(arxiv_id: str, max_pages: int = 20) -> Optional[dict]:
    """
    从缓存中获取论文解析内容
    
    Args:
        arxiv_id: 论文的arXiv ID
        max_pages: 最大页数（用于匹配缓存）
        
    Returns:
        如果找到缓存，返回包含content和use_count的字典；否则返回None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content, use_count, max_pages 
        FROM paper_content_cache 
        WHERE arxiv_id = ? AND max_pages = ?
    """, (arxiv_id, max_pages))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "content": result["content"],
            "use_count": result["use_count"],
            "max_pages": result["max_pages"]
        }
    return None

def increment_paper_content_use_count(arxiv_id: str, max_pages: int = 20) -> bool:
    """
    增加论文解析内容的使用次数
    
    Args:
        arxiv_id: 论文的arXiv ID
        max_pages: 最大页数
        
    Returns:
        是否成功更新
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE paper_content_cache 
            SET use_count = use_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE arxiv_id = ? AND max_pages = ?
        """, (arxiv_id, max_pages))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    except Exception as e:
        logger.error(f"更新使用次数失败 {arxiv_id}: {e}")
        return False

def save_paper_content_cache(arxiv_id: str, pdf_url: str, content: str, max_pages: int = 20) -> bool:
    """
    保存论文解析内容到缓存
    
    Args:
        arxiv_id: 论文的arXiv ID
        pdf_url: PDF的URL
        content: 解析后的文本内容
        max_pages: 最大页数
        
    Returns:
        是否保存成功
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 使用 INSERT OR REPLACE 来更新已存在的记录
        cursor.execute("""
            INSERT OR REPLACE INTO paper_content_cache 
            (arxiv_id, pdf_url, content, max_pages, use_count, updated_at)
            VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
        """, (arxiv_id, pdf_url, content, max_pages))
        
        conn.commit()
        conn.close()
        logger.info(f"论文解析内容已保存到缓存: {arxiv_id}")
        return True
    except Exception as e:
        logger.error(f"保存论文解析内容失败 {arxiv_id}: {e}")
        return False
