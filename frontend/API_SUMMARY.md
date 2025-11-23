# 前端 API 调用总结文档

## 基础配置

### API 实例配置

前端使用统一的 API 实例，已配置在 `src/api/index.js`：

```javascript
import api from '../api'

// API 基础配置：
// - baseURL: '/api'
// - timeout: 300000 (5分钟，匹配服务需要较长时间)
// - 自动添加 Authorization header (从 localStorage 获取 token)
// - 自动处理错误响应
```

### 认证方式

所有需要认证的接口会自动从 `localStorage.getItem('token')` 获取 token，并添加到请求头：

```
Authorization: Bearer <token>
```

---

## 1. 认证相关 API

### 1.1 用户注册

```javascript
const response = await api.post('/auth/register', {
  username: 'testuser',
  email: 'test@example.com',
  password: 'password123'
})

// 响应: { access_token: string, token_type: 'bearer' }
// 使用: localStorage.setItem('token', response.data.access_token)
```

### 1.2 用户登录

```javascript
const response = await api.post('/auth/login', {
  username: 'testuser',
  password: 'password123'
})

// 响应: { access_token: string, token_type: 'bearer' }
// 使用: localStorage.setItem('token', response.data.access_token)
```

### 1.3 获取当前用户信息

```javascript
const response = await api.get('/auth/me')

// 响应: {
//   id: number,
//   username: string,
//   email: string,
//   created_at: string
// }
```

---

## 2. 论文搜索 API

### 2.1 arXiv 论文搜索

```javascript
const response = await api.get('/papers/search', {
  params: {
    query: 'machine learning',
    max_results: 20
  }
})

// 响应: Array<{
//   arxiv_id: string,
//   title: string,
//   authors: string,
//   abstract: string,
//   published_date: string,
//   categories: string,
//   pdf_url: string
// }>
```

### 2.2 本地数据库搜索

```javascript
const response = await api.get('/papers/local-search', {
  params: {
    query: 'neural network',
    limit: 20
  }
})

// 响应: 同 2.1
```

### 2.3 获取论文分类列表

```javascript
const response = await api.get('/papers/categories')

// 响应: { categories: string[] }
```

---

## 3. AI 相关 API

### 3.1 AI 对话

```javascript
const response = await api.post('/ai/chat', {
  message: '请解释一下什么是深度学习',
  session_id: 'session_123' // 可选
})

// 响应: {
//   response: string,
//   session_id: string
// }
```

### 3.2 论文摘要生成

```javascript
const response = await api.post('/ai/summarize-paper', {
  paper_id: '2401.12345',
  summary_type: 'detailed' // 'brief' | 'detailed' | 'key_points'
})

// 响应: {
//   summary: string,
//   key_points: string[],
//   relevance_score: number
// }
```

### 3.3 获取对话历史

```javascript
const response = await api.get('/ai/conversation-history', {
  params: {
    session_id: 'session_123', // 可选，默认 'default'
    limit: 20 // 可选，默认 20
  }
})

// 响应: {
//   conversations: Array<{
//     user_message: string,
//     ai_response: string,
//     created_at: string
//   }>
// }
```

---

## 4. 爬虫相关 API

### 4.1 启动爬虫任务

```javascript
const response = await api.post('/crawler/run', {
  keywords: ['LLM', 'GPT', 'multimodal'],
  days: 30 // 可选，默认 30 天
})

// 响应: {
//   message: string,
//   status: string
// }
// 注意: 这是异步任务，接口会立即返回
```

### 4.2 获取爬虫状态

```javascript
const response = await api.get('/crawler/status')

// 响应: {
//   status: 'ready' | 'running' | 'stopped',
//   message: string
// }
```

### 4.3 停止爬虫

```javascript
const response = await api.post('/crawler/stop')

// 响应: {
//   message: string,
//   status: string
// }
```

---

## 5. 匹配相关 API

### 5.1 匹配用户需求与论文 ⭐ 核心功能

```javascript
const response = await api.post('/matching/match', {
  requirement: '企业需要AI图像识别技术用于制造业质量检测',
  top_k: 50 // 可选，默认 50
})

// 响应: {
//   papers: Array<{
//     paper_id: string,
//     title: string,
//     abstract: string,
//     authors: string,
//     published_date: string,
//     categories: string,
//     pdf_url: string,
//     score: number, // LLM 评分 (0-1)
//     reason: string, // LLM 推荐理由
//     similarity_score: number // 向量相似度 (0-1)
//   }>,
//   total: number
// }
// 注意: 此接口处理时间较长（50篇论文约需1-2分钟），已设置5分钟超时
```

### 5.2 索引论文到向量数据库

```javascript
const response = await api.post('/matching/index-papers')

// 响应: {
//   message: string,
//   status: 'started'
// }
// 注意: 这是后台任务，会立即返回
```

### 5.3 获取向量数据库统计信息

```javascript
const response = await api.get('/matching/vector-stats')

// 响应: {
//   vector_db_count: number, // 向量数据库中的论文数
//   database_count: number, // 数据库中的论文总数
//   indexed_percentage: number, // 索引完成百分比
//   unindexed_count: number, // 未索引的论文数
//   indexer_status: {
//     status: 'idle' | 'running' | 'completed' | 'error',
//     total: number,
//     processed: number,
//     skipped: number,
//     error: number,
//     message: string
//   }
// }
```

### 5.4 获取索引任务状态

```javascript
const response = await api.get('/matching/index-status')

// 响应: {
//   status: 'idle' | 'running' | 'completed' | 'error',
//   total: number,
//   processed: number,
//   skipped: number,
//   error: number,
//   message: string
// }
```

---

## 6. 错误处理

### 自动错误处理

API 实例已配置自动错误处理：

- **401**: 自动清除 token，跳转到登录页
- **403**: 显示"权限不足"
- **404**: 显示"请求的资源不存在"
- **500**: 显示"服务器内部错误"
- **超时**: 显示"请求超时，匹配服务可能需要较长时间，请稍后重试"
- **网络错误**: 显示"网络连接失败，请检查网络"

### 手动错误处理

```javascript
try {
  const response = await api.post('/matching/match', {
    requirement: 'test'
  })
  // 处理成功响应
} catch (error) {
  // error.response.data.detail 包含错误详情
  console.error('匹配失败:', error.response?.data?.detail || error.message)
}
```

---

## 7. 使用示例

### 完整工作流程示例

```javascript
import api from '../api'

// 1. 用户登录
async function login(username, password) {
  const response = await api.post('/auth/login', {
    username,
    password
  })
  localStorage.setItem('token', response.data.access_token)
  return response.data
}

// 2. 检查向量数据库状态
async function checkVectorStats() {
  const response = await api.get('/matching/vector-stats')
  console.log('向量数据库:', response.data)
  
  // 如果向量数据库为空，需要先索引论文
  if (response.data.vector_db_count === 0) {
    // 启动索引任务
    await api.post('/matching/index-papers')
    
    // 定期检查索引状态
    const interval = setInterval(async () => {
      const status = await api.get('/matching/index-status')
      console.log('索引进度:', status.data)
      
      if (status.data.status !== 'running') {
        clearInterval(interval)
      }
    }, 2000)
  }
}

// 3. 匹配论文
async function matchPapers(requirement) {
  const response = await api.post('/matching/match', {
    requirement,
    top_k: 50
  })
  return response.data.papers
}

// 4. 生成论文摘要
async function summarizePaper(paperId) {
  const response = await api.post('/ai/summarize-paper', {
    paper_id: paperId,
    summary_type: 'detailed'
  })
  return response.data
}
```

---

## 8. 注意事项

1. **认证 Token**: 登录后需要手动保存 token 到 `localStorage`
2. **超时设置**: 匹配接口已设置5分钟超时，请耐心等待
3. **异步任务**: 爬虫和索引任务都是后台执行，需要轮询状态接口
4. **错误处理**: 建议在所有 API 调用中添加 try-catch
5. **Token 过期**: Token 默认30分钟过期，需要重新登录

---

## 9. 快速参考

| 功能 | 方法 | 路径 | 认证 |
|------|------|------|------|
| 注册 | POST | `/auth/register` | ❌ |
| 登录 | POST | `/auth/login` | ❌ |
| 获取用户信息 | GET | `/auth/me` | ✅ |
| 搜索论文 | GET | `/papers/search` | ✅ |
| 本地搜索 | GET | `/papers/local-search` | ✅ |
| AI 对话 | POST | `/ai/chat` | ✅ |
| 论文摘要 | POST | `/ai/summarize-paper` | ✅ |
| 启动爬虫 | POST | `/crawler/run` | ✅ |
| 匹配论文 | POST | `/matching/match` | ✅ |
| 索引论文 | POST | `/matching/index-papers` | ✅ |
| 向量统计 | GET | `/matching/vector-stats` | ✅ |

---

## 10. 环境要求

- **开发环境**: `http://localhost:8000`
- **Vite 代理**: `/api` → `http://localhost:8000`
- **Token 存储**: `localStorage.getItem('token')`

