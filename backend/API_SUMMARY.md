# 后端 API 接口总结文档

## 基础信息

- **Base URL**: `http://localhost:8000/api`
- **API 文档**: 
  - Swagger UI: `http://localhost:8000/api/docs`
  - ReDoc: `http://localhost:8000/api/redoc`
- **认证方式**: JWT Bearer Token
- **Content-Type**: `application/json`

---

## 路由模块

后端 API 按功能分为以下模块：

- `/api/auth` - 认证相关
- `/api/papers` - 论文搜索相关
- `/api/ai` - AI 功能相关
- `/api/crawler` - 爬虫相关
- `/api/matching` - 匹配相关

---

## 1. 认证模块 (`/api/auth`)

### 1.1 用户注册

**接口**: `POST /api/auth/register`

**认证**: 不需要

**请求体**:
```python
{
    "username": str,
    "email": str,
    "password": str
}
```

**响应**:
```python
{
    "access_token": str,
    "token_type": "bearer"
}
```

**错误响应**:
- `400`: 用户名或邮箱已存在

---

### 1.2 用户登录

**接口**: `POST /api/auth/login`

**认证**: 不需要

**请求体**:
```python
{
    "username": str,
    "password": str
}
```

**响应**:
```python
{
    "access_token": str,
    "token_type": "bearer"
}
```

**错误响应**:
- `401`: 用户名或密码错误

---

### 1.3 获取当前用户信息

**接口**: `GET /api/auth/me`

**认证**: 需要 (使用 `get_current_user`)

**响应**:
```python
{
    "id": int,
    "username": str,
    "email": str,
    "created_at": str
}
```

**错误响应**:
- `401`: 未认证或 token 无效
- `404`: 用户不存在

---

## 2. 论文模块 (`/api/papers`)

### 2.1 arXiv 论文搜索

**接口**: `GET /api/papers/search`

**认证**: 需要

**查询参数**:
- `query` (str, required): 搜索关键词
- `max_results` (int, optional, default=20): 最大结果数量

**响应**: `List[PaperResponse]`

**PaperResponse 模型**:
```python
{
    "arxiv_id": str,
    "title": str,
    "authors": str,
    "abstract": str,
    "published_date": str,
    "categories": str,
    "pdf_url": str
}
```

**功能说明**:
- 调用 arXiv API 搜索论文
- 自动保存搜索结果到数据库

---

### 2.2 本地数据库搜索

**接口**: `GET /api/papers/local-search`

**认证**: 需要

**查询参数**:
- `query` (str, required): 搜索关键词
- `limit` (int, optional, default=20): 结果数量限制

**响应**: `List[PaperResponse]`

**功能说明**:
- 在本地数据库中搜索已保存的论文

---

### 2.3 获取论文分类列表

**接口**: `GET /api/papers/categories`

**认证**: 不需要

**响应**:
```python
{
    "categories": List[str]
}
```

---

## 3. AI 模块 (`/api/ai`)

### 3.1 AI 对话

**接口**: `POST /api/ai/chat`

**认证**: 需要

**请求体**:
```python
{
    "message": str,
    "session_id": Optional[str] = None
}
```

**响应**:
```python
{
    "response": str,
    "session_id": str
}
```

**功能说明**:
- 使用 OpenAI API 进行对话
- 自动保存对话记录到数据库
- 需要配置 `OPENAI_API_KEY` 环境变量

---

### 3.2 论文摘要生成

**接口**: `POST /api/ai/summarize-paper`

**认证**: 需要

**请求体**:
```python
{
    "paper_id": str,
    "summary_type": str = "brief"  # "brief" | "detailed" | "key_points"
}
```

**响应**:
```python
{
    "summary": str,
    "key_points": List[str],
    "relevance_score": float
}
```

**错误响应**:
- `404`: 论文不存在

---

### 3.3 获取对话历史

**接口**: `GET /api/ai/conversation-history`

**认证**: 需要

**查询参数**:
- `session_id` (str, optional, default="default"): 会话ID
- `limit` (int, optional, default=20): 返回数量

**响应**:
```python
{
    "conversations": List[{
        "user_message": str,
        "ai_response": str,
        "created_at": str
    }]
}
```

---

## 4. 爬虫模块 (`/api/crawler`)

### 4.1 启动爬虫任务

**接口**: `POST /api/crawler/run`

**认证**: 需要

**请求体**:
```python
{
    "keywords": List[str],
    "days": int = 30  # 爬取最近多少天的论文
}
```

**响应**:
```python
{
    "message": str,
    "status": str
}
```

**功能说明**:
- 后台异步任务，立即返回
- 爬取 arXiv 论文并自动保存到数据库
- 爬取完成后自动进行向量化处理

---

### 4.2 获取爬虫状态

**接口**: `GET /api/crawler/status`

**认证**: 需要

**响应**:
```python
{
    "status": str,  # "ready" | "running" | "stopped"
    "message": str
}
```

---

### 4.3 停止爬虫

**接口**: `POST /api/crawler/stop`

**认证**: 需要

**响应**:
```python
{
    "message": str,
    "status": str
}
```

---

## 5. 匹配模块 (`/api/matching`) ⭐ 核心模块

### 5.1 匹配用户需求与论文

**接口**: `POST /api/matching/match`

**认证**: 需要 (使用 `get_current_user_optional`，支持开发模式)

**请求体**:
```python
{
    "requirement": str,  # 用户需求文本
    "top_k": int = 50   # 返回的论文数量
}
```

**响应**:
```python
{
    "papers": List[{
        "paper_id": str,
        "title": str,
        "abstract": str,
        "authors": str,
        "published_date": str,
        "categories": str,
        "pdf_url": str,
        "score": float,  # LLM 评分 (0-1)
        "reason": str,    # LLM 推荐理由
        "similarity_score": float  # 向量相似度 (0-1)
    }],
    "total": int
}
```

**功能说明**:
1. 将用户需求转换为查询向量
2. 在向量数据库中搜索 Top-K 相似论文
3. 使用 DeepSeek LLM 对每篇论文进行评分
4. 按分数排序返回

**错误响应**:
- `400`: 需求文本为空
- `500`: 匹配失败

**注意**:
- 处理时间较长（50篇论文约需1-2分钟）
- 需要配置 `DEEPSEEK_API_KEY` 环境变量

---

### 5.2 索引论文到向量数据库

**接口**: `POST /api/matching/index-papers`

**认证**: 需要

**响应**:
```python
{
    "message": str,
    "status": "started"
}
```

**功能说明**:
- 后台异步任务，立即返回
- 将数据库中未向量化的论文索引到向量数据库
- 使用线程锁防止重复执行

**错误响应**:
- `400`: 索引任务正在运行中

---

### 5.3 获取向量数据库统计信息

**接口**: `GET /api/matching/vector-stats`

**认证**: 需要

**响应**:
```python
{
    "vector_db_count": int,      # 向量数据库中的论文数
    "database_count": int,       # 数据库中的论文总数
    "indexed_percentage": float,  # 索引完成百分比
    "unindexed_count": int,      # 未索引的论文数
    "indexer_status": {
        "status": str,           # "idle" | "running" | "completed" | "error"
        "total": int,
        "processed": int,
        "skipped": int,
        "error": int,
        "message": str
    }
}
```

---

### 5.4 获取索引任务状态

**接口**: `GET /api/matching/index-status`

**认证**: 需要

**响应**:
```python
{
    "status": str,      # "idle" | "running" | "completed" | "error"
    "total": int,
    "processed": int,
    "skipped": int,
    "error": int,
    "message": str
}
```

---

## 6. 认证机制

### 开发模式

设置环境变量 `DEBUG=True` 可以启用开发模式：

- 使用 `get_current_user_optional` 的接口可以不携带 token
- 未提供 token 时返回默认用户 `"debug_user"`

**注意**: 生产环境请务必关闭开发模式！

### 生产模式

- 所有需要认证的接口必须提供有效的 JWT token
- Token 在请求头中: `Authorization: Bearer <token>`
- Token 默认30分钟过期

---

## 7. 数据模型

### MatchingRequest
```python
{
    "requirement": str,
    "top_k": int = 50
}
```

### MatchingResponse
```python
{
    "papers": List[dict],
    "total": int
}
```

### PaperResponse
```python
{
    "arxiv_id": str,
    "title": str,
    "authors": str,
    "abstract": str,
    "published_date": str,
    "categories": str,
    "pdf_url": str
}
```

---

## 8. 错误响应格式

所有错误响应统一格式：

```python
{
    "detail": str  # 错误描述信息
}
```

### HTTP 状态码

- `200`: 成功
- `400`: 请求参数错误
- `401`: 未认证或 token 无效
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 9. 环境变量配置

后端需要配置以下环境变量：

```env
# DeepSeek API（用于论文评分）
DEEPSEEK_API_KEY=your-deepseek-api-key-here

# OpenAI API（用于AI对话和摘要）
OPENAI_API_KEY=your-openai-api-key-here

# JWT密钥
SECRET_KEY=your-super-secret-jwt-key-change-in-production

# 开发模式（可选）
DEBUG=False  # 设置为 True 启用开发模式
```

---

## 10. 依赖服务

### 向量数据库

- **技术**: ChromaDB
- **存储路径**: `chroma_db/`
- **模型**: `paraphrase-multilingual-MiniLM-L12-v2`

### 数据库

- **技术**: SQLite
- **存储路径**: `database/paper_search.db`
- **表结构**: 
  - `users` - 用户表
  - `papers` - 论文表
  - `ai_conversations` - AI对话记录表

---

## 11. 性能说明

### 匹配接口性能

- **向量搜索**: 约 1-2 秒（50篇论文）
- **LLM 评分**: 约 1-2 分钟（50篇论文，取决于 DeepSeek API 响应速度）
- **总耗时**: 约 1-3 分钟（50篇论文）

### 索引任务性能

- **处理速度**: 约 10-50 篇/秒（取决于向量化模型加载）
- **建议**: 首次索引可能需要较长时间，建议在后台执行

---

## 12. 安全注意事项

1. **JWT Secret Key**: 生产环境必须修改默认密钥
2. **API Keys**: 不要在代码中硬编码 API 密钥
3. **开发模式**: 生产环境必须关闭 `DEBUG=True`
4. **密码存储**: 使用 SHA256 哈希（生产环境建议使用 bcrypt）
5. **CORS**: 已配置允许 `localhost:5173` 和 `localhost:3000`

---

## 13. 快速参考表

| 模块 | 接口 | 方法 | 路径 | 认证 |
|------|------|------|------|------|
| 认证 | 注册 | POST | `/api/auth/register` | ❌ |
| 认证 | 登录 | POST | `/api/auth/login` | ❌ |
| 认证 | 用户信息 | GET | `/api/auth/me` | ✅ |
| 论文 | 搜索 | GET | `/api/papers/search` | ✅ |
| 论文 | 本地搜索 | GET | `/api/papers/local-search` | ✅ |
| 论文 | 分类列表 | GET | `/api/papers/categories` | ❌ |
| AI | 对话 | POST | `/api/ai/chat` | ✅ |
| AI | 论文摘要 | POST | `/api/ai/summarize-paper` | ✅ |
| AI | 对话历史 | GET | `/api/ai/conversation-history` | ✅ |
| 爬虫 | 启动 | POST | `/api/crawler/run` | ✅ |
| 爬虫 | 状态 | GET | `/api/crawler/status` | ✅ |
| 爬虫 | 停止 | POST | `/api/crawler/stop` | ✅ |
| 匹配 | 匹配论文 | POST | `/api/matching/match` | ✅ |
| 匹配 | 索引论文 | POST | `/api/matching/index-papers` | ✅ |
| 匹配 | 向量统计 | GET | `/api/matching/vector-stats` | ✅ |
| 匹配 | 索引状态 | GET | `/api/matching/index-status` | ✅ |

---

## 14. 测试建议

### 使用 Swagger UI 测试

访问 `http://localhost:8000/api/docs` 可以：
- 查看所有接口文档
- 直接在浏览器中测试接口
- 查看请求/响应示例

### 使用 curl 测试

```bash
# 登录获取 token
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}'

# 使用 token 调用接口
curl -X POST "http://localhost:8000/api/matching/match" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"requirement":"test requirement","top_k":10}'
```

