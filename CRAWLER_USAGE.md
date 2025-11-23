# 爬虫使用说明

现在系统已经集成了 `arxiv_crawler` 仓库，可以直接使用它来爬取论文。

## 功能特点

1. **自动爬取**：使用 `arxiv_crawler` 爬取 arXiv 论文
2. **自动保存**：爬取的论文自动保存到项目数据库
3. **自动索引**：爬取完成后自动进行向量化处理并索引到向量数据库

## 使用方法

### 方法一：通过API调用（推荐）

**API**: `POST /api/crawler/run`

**请求体**:
```json
{
  "keywords": ["machine learning", "deep learning", "neural networks"]
}
```

**示例（使用curl）**:
```bash
curl -X POST "http://localhost:8000/api/crawler/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["machine learning", "deep learning", "AI"]}'
```

**说明**:
- 爬虫会在后台运行
- 默认爬取最近30天的论文
- 爬取完成后会自动：
  1. 保存到项目数据库
  2. 进行向量化处理
  3. 索引到向量数据库

### 方法二：直接运行爬虫脚本

如果你想直接使用 `arxiv_crawler`，可以：

```python
import asyncio
from datetime import date, timedelta
from arxiv_crawler import ArxivScraper

# 设置日期范围
today = date.today()
days_ago = today - timedelta(days=30)

# 创建爬虫实例
scraper = ArxivScraper(
    date_from=days_ago.strftime("%Y-%m-%d"),
    date_until=today.strftime("%Y-%m-%d"),
    optional_keywords=["machine learning", "deep learning", "AI"],
    category_whitelist=["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.IR", "cs.MA"],
    trans_to=None  # 不翻译，加快速度
)

# 执行爬取
asyncio.run(scraper.fetch_all())

# 爬取完成后，论文会保存在 scraper.papers 中
print(f"共爬取 {len(scraper.papers)} 篇论文")
```

## 爬虫参数说明

### ArxivScraper 参数

- `date_from` (str): 开始日期，格式 "YYYY-MM-DD"
- `date_until` (str): 结束日期，格式 "YYYY-MM-DD"
- `optional_keywords` (list): 关键词列表，论文标题或摘要中至少包含一个关键词才会被爬取
- `category_whitelist` (list): 领域白名单，默认包含 AI 相关领域
- `category_blacklist` (list): 领域黑名单，默认为空
- `trans_to` (str|None): 翻译目标语言，设为 None 则不翻译（加快速度）

### 默认配置

- **时间范围**：最近30天
- **关键词**：用户指定
- **领域白名单**：`["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.IR", "cs.MA"]`
- **翻译**：关闭（加快速度）

## 工作流程

1. **爬取阶段**：
   - 使用 `arxiv_crawler` 异步爬取论文
   - 解析论文信息（标题、作者、摘要、分类等）

2. **保存阶段**：
   - 从论文URL提取 arxiv_id
   - 转换为项目数据库格式
   - 保存到 `backend/database/app.db`

3. **向量化阶段**：
   - 从数据库读取新爬取的论文
   - 使用 Sentence-Transformers 生成向量
   - 存储到 ChromaDB 向量数据库

## 查看爬取结果

### 检查数据库中的论文数量

```bash
# 使用SQLite命令行
sqlite3 backend/database/app.db "SELECT COUNT(*) FROM papers;"
```

### 检查向量数据库中的论文数量

**API**: `GET /api/matching/vector-stats`

```bash
curl -X GET "http://localhost:8000/api/matching/vector-stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 注意事项

1. **首次爬取**：首次爬取可能需要较长时间，取决于论文数量
2. **网络要求**：需要能够访问 arXiv 网站
3. **存储空间**：向量数据库会占用一定磁盘空间
4. **重复爬取**：系统会自动跳过已存在的论文，不会重复添加

## 常见问题

### Q: 爬虫运行失败怎么办？

A: 检查：
1. 网络连接是否正常
2. 关键词是否合理（太宽泛可能返回太多结果）
3. 查看后端日志了解详细错误信息

### Q: 如何爬取更多论文？

A: 可以：
1. 增加时间范围（修改 `date_from`）
2. 添加更多关键词
3. 扩大领域白名单

### Q: 爬取后如何验证？

A: 可以：
1. 检查数据库中的论文数量
2. 检查向量数据库统计
3. 尝试提交一个匹配请求，看是否能返回结果

## 示例：完整爬取流程

```bash
# 1. 启动爬虫
curl -X POST "http://localhost:8000/api/crawler/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["machine learning", "deep learning"]}'

# 2. 等待爬取完成（查看后端日志）

# 3. 检查统计信息
curl -X GET "http://localhost:8000/api/matching/vector-stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. 尝试匹配
curl -X POST "http://localhost:8000/api/matching/match" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"requirement": "我需要关于深度学习的论文", "top_k": 10}'
```

