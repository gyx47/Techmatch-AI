# 数据库查看指南

## 数据库文件位置

- **SQLite 数据库**: `backend/database/app.db`
- **ChromaDB 向量数据库**: `chroma_db/` 目录

## 方法一：使用查看脚本（推荐）

### 查看所有表的数据

```bash
python backend/scripts/view_database.py
```

### 查看特定表

```bash
# 查看用户表
python backend/scripts/view_database.py --table users

# 查看论文表
python backend/scripts/view_database.py --table papers

# 查看匹配历史表
python backend/scripts/view_database.py --table history

# 查看匹配结果表
python backend/scripts/view_database.py --table results

# 查看指定历史ID的匹配结果
python backend/scripts/view_database.py --table results --history-id 1
```

## 方法二：使用 SQLite 命令行工具

### Windows PowerShell

```powershell
# 进入数据库目录
cd backend\database

# 打开 SQLite 数据库
sqlite3 app.db

# 在 SQLite 命令行中执行：
.tables                    # 查看所有表
.schema                    # 查看表结构
SELECT * FROM users;       # 查看用户表
SELECT * FROM papers LIMIT 10;  # 查看前10条论文
SELECT * FROM match_history;    # 查看匹配历史
SELECT * FROM match_results;    # 查看匹配结果
.quit                      # 退出
```

### 如果没有安装 SQLite

**Windows:**
1. 下载 SQLite: https://www.sqlite.org/download.html
2. 或使用在线工具: https://sqliteviewer.app/

**或者使用 Python:**

```python
import sqlite3
from pathlib import Path

db_path = Path("backend/database/app.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("所有表:", tables)

# 查看用户表
cursor.execute("SELECT * FROM users;")
users = cursor.fetchall()
print("用户:", users)

# 查看论文表
cursor.execute("SELECT COUNT(*) FROM papers;")
count = cursor.fetchone()[0]
print(f"论文总数: {count}")

conn.close()
```

## 方法三：使用数据库查看工具

### 推荐工具

1. **DB Browser for SQLite** (免费)
   - 下载: https://sqlitebrowser.org/
   - 打开 `backend/database/app.db` 文件即可

2. **VS Code 扩展**
   - 安装 "SQLite Viewer" 扩展
   - 右键点击 `app.db` 文件，选择 "Open Database"

3. **在线工具**
   - https://sqliteviewer.app/
   - 上传 `app.db` 文件即可查看

## 数据库表结构

### 1. users - 用户表
- `id`: 用户ID
- `username`: 用户名
- `email`: 邮箱
- `password_hash`: 密码哈希
- `created_at`: 创建时间

### 2. papers - 论文表
- `id`: 论文ID
- `arxiv_id`: arXiv ID
- `title`: 标题
- `authors`: 作者
- `abstract`: 摘要
- `published_date`: 发布日期
- `categories`: 分类
- `pdf_url`: PDF链接
- `created_at`: 创建时间

### 3. match_history - 匹配历史表
- `id`: 历史ID
- `user_id`: 用户ID
- `search_desc`: 搜索描述
- `match_mode`: 匹配模式
- `result_count`: 结果数量
- `created_at`: 创建时间

### 4. match_results - 匹配结果表
- `id`: 结果ID
- `history_id`: 历史ID（外键）
- `paper_id`: 论文ID
- `title`: 标题
- `abstract`: 摘要
- `authors`: 作者
- `score`: 匹配分数
- `reason`: 推荐理由
- `match_type`: 匹配类型
- `result_order`: 排序

### 5. ai_conversations - AI对话表
- `id`: 对话ID
- `user_id`: 用户ID
- `session_id`: 会话ID
- `user_message`: 用户消息
- `ai_response`: AI回复
- `created_at`: 创建时间

## 常用 SQL 查询示例

```sql
-- 查看所有用户
SELECT * FROM users;

-- 查看论文总数
SELECT COUNT(*) FROM papers;

-- 查看最近的匹配历史
SELECT * FROM match_history ORDER BY created_at DESC LIMIT 10;

-- 查看某个用户的匹配历史
SELECT * FROM match_history WHERE user_id = 1;

-- 查看某个匹配历史的所有结果
SELECT * FROM match_results WHERE history_id = 1 ORDER BY result_order;

-- 查看匹配分数最高的论文
SELECT * FROM match_results ORDER BY score DESC LIMIT 10;

-- 统计每个用户的匹配次数
SELECT user_id, COUNT(*) as match_count 
FROM match_history 
GROUP BY user_id;
```

## 查看向量数据库（ChromaDB）

向量数据库存储在 `chroma_db/` 目录中，可以使用以下方式查看：

```python
# 使用 Python 脚本
from services.vector_service import get_vector_service

vector_service = get_vector_service()
count = vector_service.get_paper_count()
print(f"向量数据库中的论文数: {count}")

# 查看健康状态
health = vector_service.check_collection_health()
print(health)
```

