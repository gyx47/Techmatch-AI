"""
数据库配置和初始化
"""
import sqlite3
from pathlib import Path
from typing import Optional
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
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

def create_user(username: str, email: str, password_hash: str) -> int:
    """创建新用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, password_hash)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def save_paper(paper_data: dict) -> int:
    """保存论文信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO papers 
        (arxiv_id, title, authors, abstract, published_date, categories, pdf_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        paper_data.get('arxiv_id'),
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
    return paper_id

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
