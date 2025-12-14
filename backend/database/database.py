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

        # 创建需求表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requirement_id VARCHAR(50) UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                industry VARCHAR(100),
                pain_points TEXT,
                technical_level VARCHAR(50),
                market_size VARCHAR(50),
                contact_info TEXT,
                status VARCHAR(20) DEFAULT 'active',
                source VARCHAR(50) DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # 创建成果-需求匹配历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_to_requirement_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                paper_id VARCHAR(20) NOT NULL,
                paper_title TEXT,
                requirement_ids TEXT,
                match_count INTEGER DEFAULT 0,
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

        # 创建需求匹配理由表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_reasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_title TEXT NOT NULL,
                requirement_id VARCHAR(50) NOT NULL,
                reason TEXT,
                suggestion TEXT,
                estimated_time VARCHAR(50),
                success_probability VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(paper_title, requirement_id)
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
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 计算总数
    if user_id:
        cursor.execute("SELECT COUNT(*) as total FROM match_history WHERE user_id = ?", (user_id,))
    else:
        cursor.execute("SELECT COUNT(*) as total FROM match_history")
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * page_size
    if user_id:
        cursor.execute("""
            SELECT * FROM match_history 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, page_size, offset))
    else:
        cursor.execute("""
            SELECT * FROM match_history 
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (page_size, offset))
    
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

def get_requirement_by_id(requirement_id: str) -> Optional[dict]:
    """根据需求ID获取需求信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requirements WHERE requirement_id = ?", (requirement_id,))
    requirement = cursor.fetchone()
    conn.close()
    return dict(requirement) if requirement else None

def update_requirement(requirement_id: str, update_data: dict) -> bool:
    """更新需求信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 构建更新SQL
    set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
    set_clause += ', updated_at = CURRENT_TIMESTAMP'
    
    values = list(update_data.values())
    values.append(requirement_id)
    
    cursor.execute(f"""
        UPDATE requirements 
        SET {set_clause}
        WHERE requirement_id = ?
    """, values)
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success
