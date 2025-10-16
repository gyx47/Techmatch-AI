# AI论文搜索系统

基于FastAPI和Vue3的智能论文搜索平台，集成arXiv API和OpenAI GPT模型，提供智能论文搜索、AI摘要和学术对话功能。

## 🚀 技术栈

### 前端技术栈
- **核心框架**: Vue 3 - 采用组合式API (Composition API)
- **构建工具**: Vite - 极速的冷启动和热更新
- **UI组件库**: Element Plus - 成熟的组件库，快速构建专业界面
- **状态管理**: Pinia - Vue官方推荐的新一代状态管理器
- **HTTP请求**: Axios - 成熟强大的HTTP客户端

### 后端技术栈
- **核心框架**: FastAPI - 基于Python 3.8+ 类型提示的高性能Web框架
- **Web服务器**: Uvicorn - 高性能的ASGI服务器
- **数据库**: SQLite - 轻量级嵌入式数据库
- **AI集成**: OpenAI GPT模型 - 智能对话和论文摘要
- **数据源**: arXiv API - 学术论文数据

## 📁 项目结构

```
server/
├── backend/                 # 后端代码
│   ├── main.py            # FastAPI主应用
│   ├── database/          # 数据库相关
│   │   └── database.py    # 数据库配置和操作
│   ├── api/               # API路由
│   │   └── routes/        # 具体路由实现
│   │       ├── auth.py    # 用户认证
│   │       ├── papers.py  # 论文搜索
│   │       └── ai.py      # AI功能
│   └── requirements.txt   # Python依赖
├── frontend/              # 前端代码
│   ├── src/              # 源代码
│   │   ├── views/        # 页面组件
│   │   ├── stores/       # Pinia状态管理
│   │   ├── router/       # Vue Router路由
│   │   └── api/          # API接口封装
│   ├── package.json      # 前端依赖
│   └── vite.config.js    # Vite配置
├── start_backend.py       # 后端启动脚本
├── start_frontend.py      # 前端启动脚本
├── start_all.py          # 全栈启动脚本
└── README.md             # 项目说明
```

## 🛠️ 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 1. 克隆项目

```bash
git clone <repository-url>
cd server
```

### 2. 配置环境变量

复制环境变量示例文件：
```bash
cp env.example .env
```

编辑 `.env` 文件，填入必要的配置：
```env
# OpenAI API配置
OPENAI_API_KEY=your-openai-api-key-here

# JWT密钥（生产环境请使用强密钥）
SECRET_KEY=your-super-secret-jwt-key-change-in-production
```

### 3. 启动服务

#### 方式一：一键启动全栈服务
```bash
python start_all.py
```

#### 方式二：分别启动前后端

启动后端：
```bash
python start_backend.py
```

启动前端（新终端）：
```bash
python start_frontend.py
```

### 4. 访问应用

- **前端应用**: http://localhost:5173
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/api/docs

## 🔧 开发指南

### 后端开发

1. 进入backend目录：
```bash
cd backend
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 启动开发服务器：
```bash
uvicorn main:app --reload
```

### 前端开发

1. 进入frontend目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

## 📚 API文档

### 认证接口

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息

### 论文接口

- `GET /api/papers/search` - 搜索论文（arXiv API）
- `GET /api/papers/local-search` - 本地数据库搜索
- `GET /api/papers/categories` - 获取论文分类

### AI接口

- `POST /api/ai/chat` - AI对话
- `POST /api/ai/summarize-paper` - 论文摘要
- `GET /api/ai/conversation-history` - 对话历史

## 🎯 核心功能

### 1. 智能论文搜索
- 基于arXiv API的实时论文搜索
- 支持关键词、作者、分类等多种搜索方式
- 本地数据库缓存，提高搜索效率

### 2. AI学术助手
- 集成OpenAI GPT模型
- 智能论文摘要生成
- 学术问题解答和讨论
- 对话历史记录

### 3. 用户系统
- JWT身份认证
- 用户注册和登录
- 个人搜索历史

### 4. 响应式界面
- 基于Element Plus的现代化UI
- 移动端适配
- 直观的用户体验

## 🔒 安全特性

- JWT令牌认证
- 密码哈希存储
- CORS跨域配置
- 输入验证和清理

## 🚀 部署建议

### 生产环境配置

1. **环境变量**：
   - 设置强密钥
   - 配置生产数据库
   - 设置正确的CORS域名

2. **数据库**：
   - 考虑升级到PostgreSQL或MySQL
   - 配置数据库连接池

3. **服务器**：
   - 使用Nginx作为反向代理
   - 配置SSL证书
   - 设置进程管理（如PM2）

### Docker部署

```dockerfile
# 后端Dockerfile示例
FROM python:3.9-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Element Plus](https://element-plus.org/) - Vue 3组件库
- [arXiv API](https://arxiv.org/help/api) - 学术论文数据源
- [OpenAI](https://openai.com/) - AI模型服务

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交Issue
- 发送邮件
- 项目讨论区

---

**注意**: 使用OpenAI API需要有效的API密钥，请确保在环境变量中正确配置。
