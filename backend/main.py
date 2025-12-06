"""
FastAPI 主应用文件
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
# 优先加载项目根目录的 .env 文件，如果没有则加载 backend/.env
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if not env_file.exists():
    # 如果没有 .env，尝试加载 env 文件（向后兼容）
    env_file = project_root / "env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"已加载环境变量文件: {env_file}")
else:
    print("警告: 未找到 .env 文件，将使用系统环境变量")

# 导入路由
from api.routes import auth, papers, ai, crawler, matching, publish
from database.database import init_db

# Redis / ARQ 相关（用于可选的分布式任务队列）
try:
    from arq import create_pool
    from arq.connections import RedisSettings
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover - 仅在未安装相关依赖时触发
    create_pool = None  # type: ignore
    RedisSettings = None  # type: ignore
    aioredis = None  # type: ignore

# 创建FastAPI应用实例
app = FastAPI(
    title="AI论文搜索系统",
    description="基于FastAPI和Vue3的智能论文搜索平台",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vue开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(papers.router, prefix="/api/papers", tags=["论文"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(crawler.router, prefix="/api/crawler", tags=["爬虫"])
app.include_router(matching.router, prefix="/api/matching", tags=["匹配"])
app.include_router(publish.router, prefix="/api/publish", tags=["发布"])

# 静态文件服务
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库，并尝试探测 Redis / 初始化 ARQ 连接池"""
    init_db()

    # 默认关闭 Redis 模式
    app.state.use_redis = False
    app.state.redis_pool = None

    # 若未安装 arq / redis.asyncio，则直接退回本地模式
    if not (create_pool and RedisSettings and aioredis):
        print("⚠️ 未安装 arq/redis.asyncio，使用本地实现路径任务模式")
        return

    try:
        # 探测本地 Redis 是否可用
        test_client = aioredis.Redis(host="127.0.0.1", port=6379, socket_timeout=1)
        await test_client.ping()
        await test_client.close()

        # 建立 ARQ 连接池
        app.state.redis_pool = await create_pool(
            RedisSettings(host="127.0.0.1", port=6379)
        )
        app.state.use_redis = True
        print("✅ 检测到 Redis，已开启基于 ARQ 的实现路径任务队列模式")
    except Exception as e:
        print(f"⚠️ Redis 未检测到或连接失败（{e}），回退为本地实现路径任务模式")

@app.get("/")
async def root():
    """根路径，返回前端页面"""
    frontend_file = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"
    if frontend_file.exists():
        return HTMLResponse(content=frontend_file.read_text(encoding="utf-8"))
    return {"message": "AI论文搜索系统API", "docs": "/api/docs"}

@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "message": "服务运行正常"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
