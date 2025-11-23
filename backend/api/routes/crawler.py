"""
爬虫任务相关路由
"""
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List

from api.routes.auth import get_current_user
from services import crawler_service

router = APIRouter()

class CrawlRequest(BaseModel):
    keywords: List[str]
    days: int = 30  # 爬取最近多少天的论文，默认30天

@router.post("/run")
async def trigger_crawler(request: CrawlRequest, background_tasks: BackgroundTasks, current_user: str = Depends(get_current_user)):
    """
    这个API接口现在非常干净，只负责接收请求和调用服务
    """
    # 直接调用服务层处理
    return crawler_service.start_arxiv_crawl_task(
        keywords=request.keywords,
        days=request.days,
        background_tasks=background_tasks
    )

@router.get("/status")
async def get_crawl_status(current_user: str = Depends(get_current_user)):
    """获取爬虫状态"""
    return crawler_service.get_crawler_status()

@router.post("/stop")
async def stop_crawler(current_user: str = Depends(get_current_user)):
    """停止正在运行的爬虫"""
    return crawler_service.stop_crawler()