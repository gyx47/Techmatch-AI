"""
数据库配置和初始化
"""
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import logging
import json

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
        
        # 创建实现路径历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS implementation_path_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                history_id INTEGER,
                paper_ids TEXT NOT NULL,
                user_requirement TEXT NOT NULL,
                implementation_path TEXT NOT NULL,
                papers_analysis TEXT NOT NULL,
                timings TEXT,
                status VARCHAR(20) DEFAULT 'success',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (history_id) REFERENCES match_history (id) ON DELETE SET NULL
            )
        """)
        
        # 创建发布成果表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS published_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                field TEXT NOT NULL,
                description TEXT NOT NULL,
                application TEXT,
                cooperation_mode TEXT,
                contact_name TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                contact_email TEXT,
                status VARCHAR(20) DEFAULT 'published',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # 创建发布需求表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS published_needs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                industry TEXT NOT NULL,
                description TEXT NOT NULL,
                urgency_level VARCHAR(50),
                cooperation_preference TEXT,
                budget_range TEXT,
                company_name TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                contact_email TEXT,
                status VARCHAR(20) DEFAULT 'published',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

def update_user_password(user_id: int, new_password_hash: str) -> bool:
    """更新用户密码"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_password_hash, user_id))
    conn.commit()
    affected_rows = cursor.rowcount
    conn.close()
    if affected_rows > 0:
        logger.info(f"用户 {user_id} 密码更新成功")
        return True
    return False

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

def get_papers_by_query_paginated(query: str = "", page: int = 1, page_size: int = 20) -> dict:
    """根据查询条件搜索论文（分页）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 构建查询条件
    if query and query.strip():
        where_clause = "WHERE title LIKE ? OR abstract LIKE ? OR authors LIKE ?"
        params = [f"%{query}%", f"%{query}%", f"%{query}%"]
    else:
        where_clause = ""
        params = []
    
    # 计算总数
    count_sql = f"SELECT COUNT(*) as total FROM papers {where_clause}"
    cursor.execute(count_sql, params)
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * page_size
    select_sql = f"""
        SELECT * FROM papers 
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    cursor.execute(select_sql, params + [page_size, offset])
    papers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": papers
    }

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
            # 处理成果和论文的字段差异
            # 成果使用 name 和 description，论文使用 title 和 abstract
            # 为了兼容，成果也需要提供 title 和 abstract 字段（从 name 和 description 映射）
            title = result.get('title') or result.get('name')  # 成果用 name，论文用 title
            abstract = result.get('abstract') or result.get('description')  # 成果用 description，论文用 abstract
            categories = result.get('categories') or result.get('field')  # 成果用 field，论文用 categories
            
            cursor.execute("""
                INSERT INTO match_results (
                    history_id, paper_id, title, abstract, authors, categories,
                    pdf_url, published_date, score, reason, match_type, vector_score, result_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                history_id,
                result.get('paper_id'),
                title,
                abstract,
                result.get('authors'),
                categories,
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

def save_implementation_path_history(
    user_id: Optional[int],
    history_id: Optional[int],
    paper_ids: List[str],
    user_requirement: str,
    implementation_path: dict,
    papers_analysis: List[dict],
    timings: Optional[dict] = None,
    status: str = "success",
    error_message: Optional[str] = None,
) -> int:
    """
    保存实现路径历史记录
    
    Returns:
        实现路径历史记录ID
    """
    import json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO implementation_path_history (
                user_id, history_id, paper_ids, user_requirement,
                implementation_path, papers_analysis, timings, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            history_id,
            json.dumps(paper_ids),
            user_requirement,
            json.dumps(implementation_path),
            json.dumps(papers_analysis),
            json.dumps(timings) if timings else None,
            status,
            error_message,
        ))
        path_history_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"实现路径历史已保存，记录ID: {path_history_id}")
        return path_history_id
    except Exception as e:
        logger.error(f"保存实现路径历史失败: {e}")
        raise

def get_implementation_path_history_by_history_id(
    user_id: Optional[int],
    history_id: int,
) -> List[dict]:
    """
    根据匹配历史ID获取该话题下所有的实现路径历史
    
    Returns:
        实现路径历史记录列表（按创建时间倒序）
    """
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查询当前用户的记录，且 history_id 匹配，同时 JOIN match_history 获取话题信息
    cursor.execute("""
        SELECT iph.*, mh.search_desc as topic_description
        FROM implementation_path_history iph
        LEFT JOIN match_history mh ON iph.history_id = mh.id
        WHERE iph.user_id = ? AND iph.history_id = ?
        ORDER BY iph.created_at DESC
    """, (user_id, history_id))
    
    rows = cursor.fetchall()
    conn.close()
    
    # 解析 JSON 字段
    results = []
    for row in rows:
        record = dict(row)
        try:
            record["paper_ids"] = json.loads(record["paper_ids"])
            record["implementation_path"] = json.loads(record["implementation_path"])
            record["papers_analysis"] = json.loads(record["papers_analysis"])
            if record.get("timings"):
                record["timings"] = json.loads(record["timings"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"解析实现路径历史记录失败 {record.get('id')}: {e}")
            continue
        results.append(record)
    
    return results

def get_all_implementation_path_history(
    user_id: Optional[int],
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    获取当前用户的所有实现路径历史（不限制话题）
    
    Returns:
        {"total": int, "page": int, "page_size": int, "items": List[dict]}
    """
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user_id is None:
        conn.close()
        return {
            "total": 0,
            "page": page,
            "page_size": page_size,
            "items": []
        }
    
    # 计算总数
    cursor.execute("SELECT COUNT(*) as total FROM implementation_path_history WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * page_size
    cursor.execute("""
        SELECT iph.*, mh.search_desc as topic_description
        FROM implementation_path_history iph
        LEFT JOIN match_history mh ON iph.history_id = mh.id
        WHERE iph.user_id = ?
        ORDER BY iph.created_at DESC
        LIMIT ? OFFSET ?
    """, (user_id, page_size, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    # 解析 JSON 字段
    results = []
    for row in rows:
        record = dict(row)
        try:
            record["paper_ids"] = json.loads(record["paper_ids"])
            record["implementation_path"] = json.loads(record["implementation_path"])
            record["papers_analysis"] = json.loads(record["papers_analysis"])
            if record.get("timings"):
                record["timings"] = json.loads(record["timings"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"解析实现路径历史记录失败 {record.get('id')}: {e}")
            continue
        results.append(record)
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": results
    }

# =======================
# 发布成果相关函数
# =======================

def create_published_achievement(user_id: int, data: dict) -> int:
    """创建发布的成果"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 处理 JSON 字段
    cooperation_mode = json.dumps(data.get('cooperation_mode', [])) if data.get('cooperation_mode') else None
    
    cursor.execute("""
        INSERT INTO published_achievements 
        (user_id, name, field, description, application, cooperation_mode, 
         contact_name, contact_phone, contact_email, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get('name'),
        data.get('field'),
        data.get('description'),
        data.get('application'),
        cooperation_mode,
        data.get('contact_name'),
        data.get('contact_phone'),
        data.get('contact_email'),
        data.get('status', 'published')
    ))
    
    achievement_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"创建发布成果成功，ID: {achievement_id}")
    return achievement_id

def get_published_achievements(
    page: int = 1, 
    page_size: int = 20, 
    keyword: str = None, 
    field: str = None,
    user_id: int = None
) -> dict:
    """获取成果列表（分页、搜索、筛选）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 构建查询条件
    conditions = ["status = 'published'"]
    params = []
    
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    
    if keyword:
        conditions.append("(name LIKE ? OR description LIKE ? OR application LIKE ?)")
        keyword_pattern = f"%{keyword}%"
        params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
    
    if field:
        conditions.append("field = ?")
        params.append(field)
    
    where_clause = " AND ".join(conditions)
    
    # 计算总数
    cursor.execute(f"SELECT COUNT(*) as total FROM published_achievements WHERE {where_clause}", params)
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * page_size
    cursor.execute(f"""
        SELECT * FROM published_achievements 
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, params + [page_size, offset])
    
    rows = cursor.fetchall()
    conn.close()
    
    # 解析 JSON 字段
    items = []
    for row in rows:
        item = dict(row)
        if item.get('cooperation_mode'):
            try:
                item['cooperation_mode'] = json.loads(item['cooperation_mode'])
            except:
                item['cooperation_mode'] = []
        items.append(item)
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }

def get_published_achievement_by_id(achievement_id: int) -> Optional[dict]:
    """获取成果详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM published_achievements 
        WHERE id = ? AND status = 'published'
    """, (achievement_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        item = dict(row)
        # 解析 JSON 字段
        if item.get('cooperation_mode'):
            try:
                item['cooperation_mode'] = json.loads(item['cooperation_mode'])
            except:
                item['cooperation_mode'] = []
        return item
    return None

def update_published_achievement(achievement_id: int, user_id: int, data: dict) -> bool:
    """更新成果（仅发布者）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查权限
    cursor.execute("SELECT user_id FROM published_achievements WHERE id = ?", (achievement_id,))
    row = cursor.fetchone()
    if not row or row['user_id'] != user_id:
        conn.close()
        return False
    
    # 处理 JSON 字段
    cooperation_mode = json.dumps(data.get('cooperation_mode', [])) if data.get('cooperation_mode') else None
    
    cursor.execute("""
        UPDATE published_achievements 
        SET name = ?, field = ?, description = ?, application = ?, 
            cooperation_mode = ?, contact_name = ?, contact_phone = ?, 
            contact_email = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    """, (
        data.get('name'),
        data.get('field'),
        data.get('description'),
        data.get('application'),
        cooperation_mode,
        data.get('contact_name'),
        data.get('contact_phone'),
        data.get('contact_email'),
        achievement_id,
        user_id
    ))
    
    conn.commit()
    conn.close()
    logger.info(f"更新成果成功，ID: {achievement_id}")
    return True

def delete_published_achievement(achievement_id: int, user_id: int) -> bool:
    """删除成果（软删除，仅发布者）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查权限
    cursor.execute("SELECT user_id FROM published_achievements WHERE id = ?", (achievement_id,))
    row = cursor.fetchone()
    if not row or row['user_id'] != user_id:
        conn.close()
        return False
    
    cursor.execute("""
        UPDATE published_achievements 
        SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    """, (achievement_id, user_id))
    
    conn.commit()
    conn.close()
    logger.info(f"删除成果成功，ID: {achievement_id}")
    return True

# =======================
# 发布需求相关函数
# =======================

def create_published_need(user_id: int, data: dict) -> int:
    """创建发布的需求"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 处理 JSON 字段
    cooperation_preference = json.dumps(data.get('cooperation_preference', [])) if data.get('cooperation_preference') else None
    
    cursor.execute("""
        INSERT INTO published_needs 
        (user_id, title, industry, description, urgency_level, cooperation_preference, 
         budget_range, company_name, contact_name, contact_phone, contact_email, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get('title'),
        data.get('industry'),
        data.get('description'),
        data.get('urgency_level'),
        cooperation_preference,
        data.get('budget_range'),
        data.get('company_name'),
        data.get('contact_name'),
        data.get('contact_phone'),
        data.get('contact_email'),
        data.get('status', 'published')
    ))
    
    need_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"创建发布需求成功，ID: {need_id}")
    return need_id

def get_published_needs(
    page: int = 1, 
    page_size: int = 20,
    keyword: str = None, 
    industry: str = None,
    user_id: int = None
) -> dict:
    """获取需求列表（分页、搜索、筛选）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 构建查询条件
    conditions = ["status = 'published'"]
    params = []
    
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    
    if keyword:
        conditions.append("(title LIKE ? OR description LIKE ?)")
        keyword_pattern = f"%{keyword}%"
        params.extend([keyword_pattern, keyword_pattern])
    
    if industry:
        conditions.append("industry = ?")
        params.append(industry)
    
    where_clause = " AND ".join(conditions)
    
    # 计算总数
    cursor.execute(f"SELECT COUNT(*) as total FROM published_needs WHERE {where_clause}", params)
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * page_size
    cursor.execute(f"""
        SELECT * FROM published_needs 
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, params + [page_size, offset])
    
    rows = cursor.fetchall()
    conn.close()
    
    # 解析 JSON 字段
    items = []
    for row in rows:
        item = dict(row)
        if item.get('cooperation_preference'):
            try:
                item['cooperation_preference'] = json.loads(item['cooperation_preference'])
            except:
                item['cooperation_preference'] = []
        items.append(item)
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }

def get_published_need_by_id(need_id: int) -> Optional[dict]:
    """获取需求详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM published_needs 
        WHERE id = ? AND status = 'published'
    """, (need_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        item = dict(row)
        # 解析 JSON 字段
        if item.get('cooperation_preference'):
            try:
                item['cooperation_preference'] = json.loads(item['cooperation_preference'])
            except:
                item['cooperation_preference'] = []
        return item
    return None

def update_published_need(need_id: int, user_id: int, data: dict) -> bool:
    """更新需求（仅发布者）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查权限
    cursor.execute("SELECT user_id FROM published_needs WHERE id = ?", (need_id,))
    row = cursor.fetchone()
    if not row or row['user_id'] != user_id:
        conn.close()
        return False
    
    # 处理 JSON 字段
    cooperation_preference = json.dumps(data.get('cooperation_preference', [])) if data.get('cooperation_preference') else None
    
    cursor.execute("""
        UPDATE published_needs 
        SET title = ?, industry = ?, description = ?, urgency_level = ?, 
            cooperation_preference = ?, budget_range = ?, company_name = ?, 
            contact_name = ?, contact_phone = ?, contact_email = ?, 
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    """, (
        data.get('title'),
        data.get('industry'),
        data.get('description'),
        data.get('urgency_level'),
        cooperation_preference,
        data.get('budget_range'),
        data.get('company_name'),
        data.get('contact_name'),
        data.get('contact_phone'),
        data.get('contact_email'),
        need_id,
        user_id
    ))
    
    conn.commit()
    conn.close()
    logger.info(f"更新需求成功，ID: {need_id}")
    return True

def delete_published_need(need_id: int, user_id: int) -> bool:
    """删除需求（软删除，仅发布者）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查权限
    cursor.execute("SELECT user_id FROM published_needs WHERE id = ?", (need_id,))
    row = cursor.fetchone()
    if not row or row['user_id'] != user_id:
        conn.close()
        return False
    
    cursor.execute("""
        UPDATE published_needs 
        SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    """, (need_id, user_id))
    
    conn.commit()
    conn.close()
    logger.info(f"删除需求成功，ID: {need_id}")
    return True
