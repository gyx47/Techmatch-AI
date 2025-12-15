## 成果需求智能匹配平台

一个面向高校和企业的**科研成果与产业需求智能撮合平台**：  
整合 arXiv 论文库、向量检索（ChromaDB）和大型语言模型（DeepSeek），  
提供“需求 → 论文 → 合作方案 → 实现路径”的全流程智能辅助。

---

## 🚀 功能概览

- **智能需求匹配**
  - **Query Expansion**：LLM 自动扩展用户自然语言需求
  - **向量召回 + LLM 精排**：向量搜索（ChromaDB）+ Listwise LLM 重排序
  - 多维度评分与可解释推荐理由（匹配度%、匹配等级标签、推荐短评）

- **论文深度解析**
  - 自动下载 arXiv PDF 并抽取文本
  - 识别论文体裁（survey / method / benchmark / theory 等）
  - 输出核心技术、实现细节、技术优势、实现难点等结构化分析

- **实现路径生成**
  - 基于多篇候选论文的工程化分析，生成**工业级 Technical Design Doc**
  - 包含：架构决策、技术选型、实施阶段、风险评估、成功标准
  - 前端提供“科研成果实现路径”可视化对话框与一键导出 JSON

- **论文索引与评估工具**
  - 后台一键任务：将数据库论文批量向量化写入 ChromaDB
  - `backend/test/pdf/test_ragas.py`：基于 Ragas 的检索链路自动评测脚本

---

## 🧱 技术栈

- **前端**
  - **框架**：Vue 3 + Vite
  - **UI**：Element Plus，定制化首页与智能匹配页面（`SmartMatch.vue`）
  - **状态管理**：Pinia
  - **请求封装**：Axios（统一 token 注入 & 401 拦截登出重定向）

- **后端**
  - **框架**：FastAPI + Uvicorn
  - **数据库**：SQLite（业务数据）+ ChromaDB（向量库，`chroma_db/`）
  - **核心服务**：
    - `matching_service`：查询扩展 + 向量召回 + LLM 精排
    - `llm_service`：DeepSeek 封装（匹配、论文分析、实现路径生成等）
    - `vector_service`：ChromaDB 管理与相似度搜索
    - `pdf_service`：PDF 下载与文本抽取
  - **路由层**：`backend/api/routes`
    - `matching.py`：需求匹配 API
    - `papers.py`：论文分析 & 实现路径 API
    - `auth.py`：JWT 登录与用户信息

---

## 📁 项目结构（简版）

```text
server/
├── backend/
│   ├── main.py                    # FastAPI 入口
│   ├── api/routes/                # 业务路由
│   │   ├── auth.py                # 登录注册 & 用户信息
│   │   ├── matching.py            # 智能匹配接口
│   │   └── papers.py              # 论文分析 & 实现路径
│   ├── services/                  # 领域服务
│   │   ├── llm_service.py         # DeepSeek 调用与高阶封装
│   │   ├── matching_service.py    # 向量+LLM 匹配流程
│   │   ├── vector_service.py      # ChromaDB 管理
│   │   └── pdf.py                 # PDF 下载与解析
│   ├── database/                  # 数据库与 DAO
│   ├── test/pdf/test_ragas.py     # Ragas 自动评测脚本
│   └── requirements.txt           # 后端依赖
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue           # 首页
│   │   │   ├── SmartMatch.vue     # 智能匹配 & 实现路径
│   │   │   └── UserProfile.vue    # 个人中心
│   │   ├── stores/user.js         # 用户登录状态
│   │   ├── router/index.js        # 路由 & 登录拦截
│   │   └── api/index.js           # Axios 实例与拦截器
│   └── package.json
├── start_backend.py               # 本地后端启动脚本
├── start_frontend.py              # 本地前端启动脚本
├── start_all.py                   # 一键启前后端
└── README.md
```

---

## 🛠 环境准备与启动

### 环境要求

- **Python** = 3.11 （高级别不兼容）  
- **Node.js** ≥ 16  
- 推荐使用 **虚拟环境**（`venv` / `conda`）

### 1️⃣ 克隆项目

```bash
git clone <your-repo-url>
cd server
```

### 2️⃣ 配置环境变量

在项目根目录或 `backend/` 下创建 `.env`（可以参考现有示例）：

```env
# DeepSeek OpenAI 兼容接口
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_API_BASE=https://api.deepseek.com

# JWT 密钥
SECRET_KEY=your-super-secret-jwt-key
```

### 3️⃣ 安装依赖

- **后端**

```bash
cd backend
pip install -r requirements.txt
```

- **前端**

```bash
cd frontend
npm install
```

### 4️⃣ 启动服务

- **一键启动（开发环境）**

```bash
cd server
python start_all.py
```

- **分别启动**

```bash
# 终端 1：后端
cd backend
uvicorn main:app --reload --port 8000

# 终端 2：前端
cd frontend
npm run dev -- --port 5173
```

### 5️⃣ 访问地址

- **前端应用**：`http://localhost:5173`  
- **后端 API 根路径**：`http://localhost:8000`  
- **Swagger 文档**：`http://localhost:8000/api/docs`

---

## 🔍 核心业务流程

### 智能匹配（`POST /api/matching/match`）

- **输入**：用户自然语言需求
- **流程**：
  - LLM Query Expansion → 向量召回 TopK 论文 → LLM Listwise 精排
  - 输出匹配度分数（0–100）、匹配等级标签、推荐理由

### 实现路径生成（`POST /api/papers/generate-implementation-path`）

- 选择多篇论文 → 并发下载与精读分析 → 生成结构化实现路径 JSON：
  - 架构决策（architectural_decision）
  - 系统架构与技术栈（system_architecture）
  - 开发 Roadmap（development_roadmap_detailed）
  - 风险与缓解措施（risk_mitigation）

---

## 🧪 测试与评估

- **检索评测脚本**：`backend/test/pdf/test_ragas.py`
  - 并发处理本地 PDF，自动生成测试问题
  - 调用匹配接口验证能否召回原论文
  - 若安装 Ragas，可进一步评估 faithfulness / context_precision / context_recall 等指标

运行示例：

```bash
cd backend
python -m test.pdf.test_ragas
```

---

## 🔒 鉴权与安全

- 后端使用 JWT 进行身份认证，受保护接口依赖 `get_current_user` / `get_current_user_optional`
- 前端：
  - Axios 响应拦截器统一处理 401：自动登出并跳转登录页（携带 redirect）
  - 路由 `meta.requiresAuth` + `beforeEach` 实现前端访问控制

---

## 📄 许可证与贡献

- **许可证**：MIT License（详见 `LICENSE`）  
- **贡献方式**：
  - Fork 仓库
  - 创建特性分支并提交 PR
  - 描述清楚改动目的与影响

欢迎在实际科研 / 产业项目中使用本平台，也欢迎提 Issue / PR 一起把「成果需求智能匹配」做得更好。


