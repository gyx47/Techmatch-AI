# Apifox 认证配置指南

## 问题：403 Not authenticated

当你在 Apifox 中测试 API 时遇到 `403 Not authenticated` 错误，说明请求缺少认证信息。

## 解决方案

### 方案一：在 Apifox 中配置认证（推荐）

#### 步骤 1：先获取 Token

1. 在 Apifox 中调用登录接口：
   - **Method**: `POST`
   - **URL**: `http://localhost:8000/api/auth/login`
   - **Body** (JSON):
     ```json
     {
       "username": "testuser",
       "password": "testpass"
     }
     ```
   - 如果没有账号，先调用注册接口：
     - **URL**: `http://localhost:8000/api/auth/register`
     - **Body**:
       ```json
       {
         "username": "testuser",
         "email": "test@example.com",
         "password": "testpass"
       }
       ```

2. 从响应中复制 `access_token`：
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer"
   }
   ```

#### 步骤 2：在 Apifox 中配置认证

**方法 A：在请求的 Headers 中添加**

1. 在 Apifox 的请求界面，点击 **"Headers"** 标签
2. 点击 **"添加"** 按钮
3. 添加以下 Header：
   - **Key**: `Authorization`
   - **Value**: `Bearer <你的token>`
   - 例如：`Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**方法 B：在 Apifox 项目级别配置（推荐）**

1. 点击 Apifox 左侧的 **"项目设置"** 或 **"环境变量"**
2. 找到 **"认证"** 或 **"Authorization"** 设置
3. 选择 **"Bearer Token"** 类型
4. 在 Token 字段中填入你的 `access_token`
5. 这样所有请求都会自动携带这个 token

**方法 C：使用环境变量**

1. 在 Apifox 的 **"环境变量"** 中创建一个变量：
   - **变量名**: `token`
   - **变量值**: `你的access_token`
2. 在请求的 Headers 中使用：
   - **Key**: `Authorization`
   - **Value**: `Bearer {{token}}`

### 方案二：使用开发模式（临时跳过认证）

我已经为你添加了开发模式支持，可以临时跳过认证。

#### 步骤 1：设置环境变量

在 `.env` 文件中添加：
```env
DEBUG=True
```

或者在启动时设置：
```bash
# Windows PowerShell
$env:DEBUG="True"; python start_backend.py

# Windows CMD
set DEBUG=True && python start_backend.py

# Linux/Mac
DEBUG=True python start_backend.py
```

#### 步骤 2：重启后端服务

重启后，所有使用 `get_current_user_optional` 的接口都可以不携带 token 访问。

**注意**：开发模式仅用于本地调试，生产环境请务必关闭！

### 方案三：快速测试 Token

使用以下 Python 脚本快速生成一个测试 token：

```python
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

# 创建测试 token
data = {"sub": "testuser"}
expire = datetime.utcnow() + timedelta(days=1)
data.update({"exp": expire})

token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
print(f"Bearer {token}")
```

## 在 Apifox 中测试匹配接口

配置好认证后，测试 `/api/matching/match` 接口：

1. **Method**: `POST`
2. **URL**: `http://localhost:8000/api/matching/match`
3. **Headers**: 
   ```
   Authorization: Bearer <你的token>
   Content-Type: application/json
   ```
4. **Body** (JSON):
   ```json
   {
     "requirement": "企业需要AI图像识别技术用于制造业质量检测",
     "top_k": 50
   }
   ```

## 常见问题

### Q: Token 过期了怎么办？
A: Token 默认 30 分钟过期，重新调用登录接口获取新 token。

### Q: 如何查看当前 token 是否有效？
A: 调用 `GET /api/auth/me` 接口，如果返回用户信息说明 token 有效。

### Q: 开发模式安全吗？
A: 不安全！仅用于本地开发调试，生产环境必须关闭。

## 推荐工作流程

1. **开发阶段**：使用开发模式（`DEBUG=True`）快速测试
2. **测试阶段**：在 Apifox 中配置项目级别的 Bearer Token
3. **生产环境**：确保 `DEBUG=False`，所有接口必须认证

