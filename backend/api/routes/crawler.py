"""
爬虫任务相关路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

from api.routes.auth import get_current_user
from services.crawler_service import start_crawler, crawler_status, stop_crawler

router = APIRouter()

class CrawlRequest(BaseModel):
    keywords: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    date_from: str
    date_until: str

    @field_validator("date_from", "date_until")
    @classmethod
    def validate_date(cls, v: str):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except Exception:
            raise ValueError("日期格式应为 YYYY-MM-DD")
        return v

class CrawlStartResponse(BaseModel):
    pid: int
    running: bool

class CrawlStatusResponse(BaseModel):
    running: bool
    returncode: Optional[int] = None
    pid: Optional[int] = None

@router.post("/start", response_model=CrawlStartResponse)
async def start_crawl(req: CrawlRequest, current_user: str = Depends(get_current_user)):
    try:
        pid = start_crawler(req.date_from, req.date_until, req.keywords, req.categories)
        status = crawler_status()
        return {"pid": pid, "running": status.get("running", False)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动爬虫失败: {str(e)}")

@router.get("/status", response_model=CrawlStatusResponse)
async def get_crawl_status(current_user: str = Depends(get_current_user)):
    return crawler_status()

@router.post("/stop")
async def stop_crawl(current_user: str = Depends(get_current_user)):
    ok = stop_crawler()
    return {"stopped": ok}


