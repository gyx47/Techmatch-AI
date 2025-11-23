# 数据索引指南

当向量数据库为空时，需要先爬取数据并建立向量索引。有两种方式：

## 方式一：使用爬虫API（推荐）

爬虫会自动将爬取的论文添加到向量数据库。

### 1. 启动爬虫任务

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
  -d '{"keywords": ["machine learning", "deep learning"]}'
```

**说明**:
- 爬虫会在后台运行，爬取最近30天的论文
- 爬取完成后会自动进行向量化处理
- 可以通过后端日志查看进度

### 2. 检查向量数据库状态

**API**: `GET /api/matching/vector-stats`

**响应**:
```json
{
  "vector_db_count": 150,
  "database_count": 200,
  "indexed_percentage": 75.0
}
```

## 方式二：索引现有数据库中的论文

如果数据库中已有论文但向量数据库为空，可以使用索引API。

### 1. 使用API索引（推荐）

**API**: `POST /api/matching/index-papers`

**示例（使用curl）**:
```bash
curl -X POST "http://localhost:8000/api/matching/index-papers" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**说明**:
- 这是一个后台任务，会立即返回
- 会将数据库中所有论文添加到向量数据库
- 自动跳过已存在的论文
- 可以通过后端日志查看进度

### 2. 使用命令行脚本

**运行脚本**:
```bash
cd backend
python scripts/index_existing_papers.py
```

**说明**:
- 脚本会读取数据库中的所有论文
- 将每篇论文的标题和摘要转换为向量
- 存储到ChromaDB向量数据库
- 显示处理进度和统计信息

## 方式三：前端操作（如果已实现）

如果前端有爬虫管理界面，可以直接在前端操作：
1. 进入爬虫管理页面
2. 输入关键词（如：machine learning, AI, deep learning）
3. 点击"开始爬取"
4. 等待爬取和索引完成

## 验证索引是否成功

### 1. 检查向量数据库统计

```bash
curl -X GET "http://localhost:8000/api/matching/vector-stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. 尝试匹配

提交一个匹配请求，如果返回了论文结果，说明索引成功。

## 常见问题

### Q: 为什么向量数据库是空的？

A: 可能的原因：
1. 还没有运行过爬虫
2. 爬虫运行失败
3. 数据库中没有论文数据

### Q: 索引需要多长时间？

A: 取决于论文数量：
- 每篇论文的向量化大约需要0.1-0.5秒
- 100篇论文大约需要10-50秒
- 1000篇论文大约需要2-8分钟

### Q: 可以重复索引吗？

A: 可以，系统会自动跳过已存在的论文，不会重复添加。

### Q: 如何查看索引进度？

A: 查看后端日志输出，会显示：
- 已处理的论文数量
- 跳过的论文数量
- 处理失败的论文数量

## 推荐工作流程

1. **首次使用**：
   - 使用爬虫API爬取一些论文（建议关键词：machine learning, AI, deep learning）
   - 等待爬取和索引完成（查看日志）
   - 检查向量数据库统计

2. **定期更新**：
   - 每周或每月运行一次爬虫
   - 爬虫会自动处理新论文的向量化

3. **补充索引**：
   - 如果发现数据库中有论文但向量数据库为空
   - 使用索引API或脚本进行批量索引

## 注意事项

1. **依赖安装**：确保已安装 `sentence-transformers` 和 `chromadb`
   ```bash
   pip install sentence-transformers chromadb torch
   ```

2. **磁盘空间**：向量数据库会占用一定磁盘空间，每篇论文约几KB

3. **性能**：首次索引可能需要较长时间，建议在后台运行

4. **日志**：索引过程中的详细信息会输出到后端日志中

