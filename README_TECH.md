# 技术实现说明

## 完整技术路线

### 1. 论文爬取与向量化
- **爬虫服务** (`backend/services/crawler_service.py`)
  - 爬取 arXiv 论文后，立即进行向量化处理
  - 使用 Sentence-Transformers 将论文标题和摘要转换为向量
  - 存储到 ChromaDB 向量数据库

### 2. 向量搜索
- **向量服务** (`backend/services/vector_service.py`)
  - 使用 `paraphrase-multilingual-MiniLM-L12-v2` 模型（支持中英文）
  - ChromaDB 持久化存储，使用余弦相似度搜索
  - 将用户需求文本转换为查询向量

### 3. LLM 评分
- **LLM 服务** (`backend/services/llm_service.py`)
  - 调用 DeepSeek API 对每篇论文进行深度评估
  - 返回匹配得分（0-1）和详细推荐理由
  - 批量处理，逐一评分避免并发过多

### 4. 匹配服务
- **匹配服务** (`backend/services/matching_service.py`)
  - 整合向量搜索和 LLM 评分
  - 流程：向量搜索 → 获取论文详情 → LLM 评分 → 排序返回

## API 接口

### POST /api/matching/match
匹配用户需求与论文

**请求体：**
```json
{
  "requirement": "企业需要AI图像识别技术用于制造业质量检测",
  "top_k": 50
}
```

**响应：**
```json
{
  "papers": [
    {
      "paper_id": "2401.12345",
      "title": "Deep Learning for Image Recognition",
      "abstract": "...",
      "authors": "Zhang, Li",
      "score": 0.95,
      "reason": "该论文提出的深度学习方法完全匹配企业需求...",
      "similarity_score": 0.87,
      "pdf_url": "..."
    }
  ],
  "total": 50
}
```

## 环境变量配置

在 `.env` 文件中配置：

```env
DEEPSEEK_API_KEY=your-deepseek-api-key-here
```

## 依赖安装

```bash
pip install sentence-transformers chromadb torch httpx
```

## 工作流程

1. **爬虫启动** → 爬取论文 → **自动向量化** → 存储到 ChromaDB
2. **用户提交需求** → 转换为查询向量 → **向量搜索** → 返回 Top-K 论文ID
3. **LLM 评分** → 逐一审查论文 → **生成得分和理由** → 排序返回

## 数据流

```
用户需求文本
    ↓
向量化 (Sentence-Transformers)
    ↓
ChromaDB 相似性搜索 (Top-K=50)
    ↓
获取论文详细信息 (SQLite)
    ↓
DeepSeek LLM 评分 (逐一处理)
    ↓
按得分排序
    ↓
返回给前端
```

