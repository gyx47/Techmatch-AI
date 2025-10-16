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

# 导入路由
from api.routes import auth, papers, ai, crawler
from database.database import init_db

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

# 静态文件服务
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_db()

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
