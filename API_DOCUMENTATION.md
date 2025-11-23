# 前后端接口文档

## 基础信息

- **Base URL**: `http://localhost:8000/api`
- **认证方式**: JWT Bearer Token
- **Content-Type**: `application/json`

### 认证说明

大部分接口需要认证，请求时需要在 Header 中携带：

```
Authorization: Bearer <access_token>
```

获取 token 的方式：通过 `/api/auth/login` 或 `/api/auth/register` 接口获取。

---

## 1. 认证接口

### 1.1 用户注册

**接口**: `POST /api/auth/register`

**认证**: 不需要

**请求体**:
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**错误响应**:
- `400`: 用户名或邮箱已存在
- `500`: 服务器错误

---

### 1.2 用户登录

**接口**: `POST /api/auth/login`

**认证**: 不需要

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**错误响应**:
- `401`: 用户名或密码错误
- `500`: 服务器错误

---

### 1.3 获取当前用户信息

**接口**: `GET /api/auth/me`

**认证**: 需要

**响应**:
```json
{
  "id": 1,
  "username": "string",
  "email": "string",
  "created_at": "2024-01-01 00:00:00"
}
```

**错误响应**:
- `401`: 未认证或token无效
- `404`: 用户不存在

---

## 2. 论文搜索接口

### 2.1 arXiv 论文搜索

**接口**: `GET /api/papers/search`

**认证**: 需要

**查询参数**:
- `query` (string, required): 搜索关键词
- `max_results` (int, optional, default=20): 最大结果数量

**示例**: `GET /api/papers/search?query=machine+learning&max_results=20`

**响应**:
```json
[
  {
    "arxiv_id": "2401.12345",
    "title": "Deep Learning for Image Recognition",
    "authors": "Zhang, Li; Wang, Wei",
    "abstract": "This paper presents...",
    "published_date": "2024-01-15",
    "categories": "cs.CV, cs.AI",
    "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf"
  }
]
```

**错误响应**:
- `401`: 未认证
- `500`: 搜索失败

---

### 2.2 本地数据库搜索

**接口**: `GET /api/papers/local-search`

**认证**: 需要

**查询参数**:
- `query` (string, required): 搜索关键词
- `limit` (int, optional, default=20): 结果数量限制

**示例**: `GET /api/papers/local-search?query=neural+network&limit=10`

**响应**: 同 2.1

**错误响应**:
- `401`: 未认证
- `500`: 搜索失败

---

### 2.3 获取论文分类列表

**接口**: `GET /api/papers/categories`

**认证**: 不需要

**响应**:
```json
{
  "categories": [
    "cs.AI", "cs.CL", "cs.CC", "cs.CE", "cs.CG", 
    "cs.GT", "cs.CV", "cs.CY", ...
  ]
}
```

---

## 3. AI 接口

### 3.1 AI 对话

**接口**: `POST /api/ai/chat`

**认证**: 需要

**请求体**:
```json
{
  "message": "请解释一下什么是深度学习",
  "session_id": "session_123"  // 可选
}
```

**响应**:
```json
{
  "response": "深度学习是机器学习的一个分支...",
  "session_id": "session_123"
}
```

**错误响应**:
- `401`: 未认证
- `500`: AI服务错误

---

### 3.2 论文摘要生成

**接口**: `POST /api/ai/summarize-paper`

**认证**: 需要

**请求体**:
```json
{
  "paper_id": "2401.12345",
  "summary_type": "brief"  // brief, detailed, key_points
}
```

**响应**:
```json
{
  "summary": "这篇论文提出了...",
  "key_points": [
    "关键点1",
    "关键点2",
    "关键点3"
  ],
  "relevance_score": 0.85
}
```

**错误响应**:
- `401`: 未认证
- `404`: 论文不存在
- `500`: 生成失败

---

### 3.3 获取对话历史

**接口**: `GET /api/ai/conversation-history`

**认证**: 需要

**查询参数**:
- `session_id` (string, optional, default="default"): 会话ID
- `limit` (int, optional, default=20): 返回数量

**示例**: `GET /api/ai/conversation-history?session_id=session_123&limit=50`

**响应**:
```json
{
  "conversations": [
    {
      "user_message": "什么是机器学习？",
      "ai_response": "机器学习是...",
      "created_at": "2024-01-01 12:00:00"
    }
  ]
}
```

**错误响应**:
- `401`: 未认证
- `500`: 获取失败

---

## 4. 爬虫接口

### 4.1 启动爬虫任务

**接口**: `POST /api/crawler/run`

**认证**: 需要

**说明**: 启动后台爬虫任务，爬取论文后会自动进行向量化处理并存储到向量数据库。

**请求体**:
```json
{
  "keywords": ["LLM", "GPT", "multimodal"]
}
```

**响应**:
```json
{
  "message": "爬虫任务已在后台启动",
  "keywords": ["LLM", "GPT", "multimodal"]
}
```

**错误响应**:
- `401`: 未认证
- `500`: 启动失败

**注意**: 这是一个异步任务，接口会立即返回，爬虫在后台执行。

---

### 4.2 获取爬虫状态

**接口**: `GET /api/crawler/status`

**认证**: 需要

**响应**:
```json
{
  "status": "ready",
  "message": "爬虫服务就绪"
}
```

**错误响应**:
- `401`: 未认证

---

## 5. 匹配接口

### 5.1 匹配用户需求与论文

**接口**: `POST /api/matching/match`

**认证**: 需要

**说明**: 
1. 将用户需求转换为查询向量
2. 在向量数据库中搜索 Top-K 相似论文
3. 使用 DeepSeek LLM 对每篇论文进行评分
4. 按分数排序返回

**请求体**:
```json
{
  "requirement": "企业需要AI图像识别技术用于制造业质量检测",
  "top_k": 50
}
```

**响应**:
```json
{
  "papers": [
    {
      "paper_id": "2401.12345",
      "title": "Deep Learning for Image Recognition in Manufacturing",
      "abstract": "This paper presents a novel approach...",
      "authors": "Zhang, Li; Wang, Wei",
      "published_date": "2024-01-15",
      "categories": "cs.CV, cs.AI",
      "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
      "score": 0.95,
      "reason": "该论文提出的深度学习方法完全匹配企业需求，可以直接应用于制造业质量检测场景。论文中的技术方案成熟，实验结果表明准确率达到98%以上。",
      "similarity_score": 0.87
    }
  ],
  "total": 50
}
```

**字段说明**:
- `score`: LLM 评分（0-1），分数越高表示匹配度越高
- `reason`: LLM 给出的详细推荐理由
- `similarity_score`: 向量相似度分数（0-1）
- `paper_id`: 论文ID（arxiv_id）

**错误响应**:
- `400`: 需求文本为空
- `401`: 未认证
- `500`: 匹配失败

**注意**: 
- 该接口会调用 DeepSeek API 对每篇论文进行评分，可能需要较长时间（50篇论文约需1-2分钟）
- 需要配置 `DEEPSEEK_API_KEY` 环境变量

---

## 6. 通用响应格式

### 成功响应

大多数接口直接返回数据，格式根据接口而定。

### 错误响应

```json
{
  "detail": "错误描述信息"
}
```

### HTTP 状态码

- `200`: 成功
- `400`: 请求参数错误
- `401`: 未认证或token无效
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 7. 前端调用示例

### JavaScript/TypeScript (Axios)

```javascript
import axios from 'axios'

// 配置基础URL和拦截器
const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 请求拦截器：添加token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 登录示例
async function login(username, password) {
  const response = await api.post('/auth/login', {
    username,
    password
  })
  localStorage.setItem('token', response.data.access_token)
  return response.data
}

// 匹配论文示例
async function matchPapers(requirement, topK = 50) {
  const response = await api.post('/matching/match', {
    requirement,
    top_k: topK
  })
  return response.data
}

// 启动爬虫示例
async function startCrawler(keywords) {
  const response = await api.post('/crawler/run', {
    keywords
  })
  return response.data
}
```

---

## 8. 环境变量配置

后端需要配置以下环境变量（在 `.env` 文件中）：

```env
# DeepSeek API（用于论文评分）
DEEPSEEK_API_KEY=your-deepseek-api-key-here

# OpenAI API（用于AI对话和摘要）
OPENAI_API_KEY=your-openai-api-key-here

# JWT密钥
SECRET_KEY=your-super-secret-jwt-key-change-in-production
```

---

## 9. 完整工作流程示例

### 场景：用户提交需求并获取匹配论文

1. **用户登录**
   ```http
   POST /api/auth/login
   {
     "username": "user123",
     "password": "password123"
   }
   ```
   返回 token，保存到 localStorage

2. **启动爬虫（可选，如果向量数据库为空）**
   ```http
   POST /api/crawler/run
   {
     "keywords": ["LLM", "GPT", "multimodal"]
   }
   ```
   等待爬虫完成（后台执行，约5-10分钟）

3. **提交需求并匹配论文**
   ```http
   POST /api/matching/match
   {
     "requirement": "企业需要AI图像识别技术用于制造业质量检测",
     "top_k": 50
   }
   ```
   返回匹配的论文列表，按得分排序

4. **查看论文详情（可选）**
   ```http
   GET /api/papers/search?query=2401.12345&max_results=1
   ```

5. **生成论文摘要（可选）**
   ```http
   POST /api/ai/summarize-paper
   {
     "paper_id": "2401.12345",
     "summary_type": "detailed"
   }
   ```

---

## 10. 注意事项

1. **认证**: 大部分接口需要 JWT token，请确保在请求头中携带
2. **异步任务**: 爬虫任务是异步执行的，接口会立即返回
3. **LLM 评分**: 匹配接口会调用 DeepSeek API，处理时间较长（50篇论文约1-2分钟）
4. **向量数据库**: 首次使用前需要先运行爬虫任务，将论文向量化并存储
5. **错误处理**: 建议前端实现统一的错误处理机制，特别是 401 错误需要重新登录

---

## 11. API 文档访问

FastAPI 自动生成的交互式 API 文档：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

可以在浏览器中直接测试所有接口。

