# 什么时候调用爬取功能

## 需要调用爬虫的场景

### 1. **首次使用系统** ⭐ 必须
- **情况**：系统刚部署，数据库和向量数据库都是空的
- **操作**：立即运行爬虫，建立初始数据
- **建议关键词**：`["machine learning", "deep learning", "AI", "neural networks"]`
- **预期结果**：爬取几百到几千篇论文，建立基础数据

### 2. **向量数据库为空** ⭐ 必须
- **情况**：匹配功能返回"未找到相似论文"
- **检查方法**：调用 `GET /api/matching/vector-stats` 查看 `vector_db_count`
- **操作**：
  - 如果数据库有论文但向量数据库为空 → 使用索引API
  - 如果数据库也为空 → 先运行爬虫

### 3. **定期更新数据** ⭐ 推荐
- **频率**：每周或每两周一次
- **目的**：获取最新的论文
- **建议**：设置定时任务或手动触发
- **时间范围**：最近7-30天

### 4. **扩展研究领域** 
- **情况**：需要特定领域的论文
- **操作**：使用特定关键词运行爬虫
- **示例**：
  - 计算机视觉：`["computer vision", "image recognition", "object detection"]`
  - 自然语言处理：`["NLP", "transformer", "BERT", "GPT"]`
  - 强化学习：`["reinforcement learning", "RL", "DQN"]`

### 5. **匹配结果不理想**
- **情况**：匹配功能返回的论文相关性不高
- **可能原因**：数据量不足或领域不匹配
- **操作**：运行爬虫，增加相关领域的论文

## 调用时机建议

### 最佳实践

1. **系统初始化时**
   ```
   部署系统 → 运行爬虫 → 等待完成 → 开始使用
   ```

2. **定期维护**
   ```
   每周一早上 → 运行爬虫 → 更新最新论文
   ```

3. **按需更新**
   ```
   发现数据不足 → 运行爬虫 → 补充数据
   ```

## 如何判断是否需要爬取

### 检查清单

- [ ] 向量数据库中有论文吗？（调用 `/api/matching/vector-stats`）
- [ ] 匹配功能能返回结果吗？
- [ ] 最近是否更新过数据？（超过1周建议更新）
- [ ] 是否需要特定领域的论文？

### 如果满足以下任一条件，建议运行爬虫：

1. ✅ `vector_db_count` 为 0
2. ✅ 匹配功能返回空结果
3. ✅ 距离上次爬取超过1周
4. ✅ 需要特定领域的论文

## 调用方式

### 方式一：通过API（推荐）

```bash
# 检查状态
curl -X GET "http://localhost:8000/api/matching/vector-stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 如果需要爬取，运行爬虫
curl -X POST "http://localhost:8000/api/crawler/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["machine learning", "deep learning", "AI"]}'
```

### 方式二：前端界面（如果已实现）

在Dashboard或管理页面点击"更新数据"按钮

### 方式三：定时任务

设置cron任务，每周自动运行一次

## 注意事项

1. **首次爬取**：可能需要10-30分钟，取决于论文数量
2. **网络要求**：需要能访问arXiv网站
3. **存储空间**：确保有足够磁盘空间
4. **避免重复**：系统会自动跳过已存在的论文

## 示例工作流

### 场景1：首次部署

```bash
# 1. 检查状态（应该返回0）
curl -X GET "http://localhost:8000/api/matching/vector-stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. 运行爬虫
curl -X POST "http://localhost:8000/api/crawler/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["machine learning", "deep learning"]}'

# 3. 等待10-30分钟（查看后端日志）

# 4. 再次检查状态
curl -X GET "http://localhost:8000/api/matching/vector-stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 5. 测试匹配功能
curl -X POST "http://localhost:8000/api/matching/match" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"requirement": "我需要关于深度学习的论文", "top_k": 10}'
```

### 场景2：定期更新

```bash
# 每周一早上运行
curl -X POST "http://localhost:8000/api/crawler/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["machine learning", "deep learning", "AI"]}'
```

### 场景3：补充特定领域

```bash
# 需要计算机视觉相关论文
curl -X POST "http://localhost:8000/api/crawler/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["computer vision", "image recognition", "object detection"]}'
```

