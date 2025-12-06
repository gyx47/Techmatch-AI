"""
发布成果与需求相关路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from database.database import (
    create_published_achievement,
    get_published_achievements,
    get_published_achievement_by_id,
    update_published_achievement,
    delete_published_achievement,
    create_published_need,
    get_published_needs,
    get_published_need_by_id,
    update_published_need,
    delete_published_need,
    get_user_by_username,
)
from api.routes.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# =======================
# 请求/响应模型
# =======================

class AchievementCreate(BaseModel):
    name: str
    field: str
    description: str
    application: Optional[str] = None
    cooperation_mode: Optional[List[str]] = None
    contact_name: str
    contact_phone: str
    contact_email: Optional[str] = None

class AchievementUpdate(BaseModel):
    name: Optional[str] = None
    field: Optional[str] = None
    description: Optional[str] = None
    application: Optional[str] = None
    cooperation_mode: Optional[List[str]] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None

class NeedCreate(BaseModel):
    title: str
    industry: str
    description: str
    urgency_level: Optional[str] = None
    cooperation_preference: Optional[List[str]] = None
    budget_range: Optional[str] = None
    company_name: str
    contact_name: str
    contact_phone: str
    contact_email: Optional[str] = None

class NeedUpdate(BaseModel):
    title: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    urgency_level: Optional[str] = None
    cooperation_preference: Optional[List[str]] = None
    budget_range: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None

# =======================
# 成果相关接口
# =======================

@router.post("/achievement")
async def publish_achievement(
    achievement: AchievementCreate,
    current_user: str = Depends(get_current_user)
):
    """发布成果"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        if user['role'] != 'researcher':
            raise HTTPException(status_code=403, detail="只有科研人员可以发布成果")
        
        achievement_id = create_published_achievement(user['id'], achievement.dict())
        return {
            "message": "成果发布成功",
            "id": achievement_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发布成果失败: {e}")
        raise HTTPException(status_code=500, detail=f"发布成果失败: {str(e)}")

@router.get("/achievements")
async def get_achievements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    field: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """获取成果列表"""
    try:
        result = get_published_achievements(
            page=page,
            page_size=page_size,
            keyword=keyword,
            field=field
        )
        return result
    except Exception as e:
        logger.error(f"获取成果列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取成果列表失败: {str(e)}")

@router.get("/achievement/{achievement_id}")
async def get_achievement_detail(
    achievement_id: int,
    current_user: str = Depends(get_current_user)
):
    """获取成果详情"""
    try:
        achievement = get_published_achievement_by_id(achievement_id)
        if not achievement:
            raise HTTPException(status_code=404, detail="成果不存在")
        return achievement
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取成果详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取成果详情失败: {str(e)}")

@router.put("/achievement/{achievement_id}")
async def update_achievement(
    achievement_id: int,
    achievement: AchievementUpdate,
    current_user: str = Depends(get_current_user)
):
    """更新成果（仅发布者）"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 只更新提供的字段
        update_data = {k: v for k, v in achievement.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的字段")
        
        success = update_published_achievement(achievement_id, user['id'], update_data)
        if not success:
            raise HTTPException(status_code=403, detail="无权修改此成果或成果不存在")
        
        return {"message": "成果更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新成果失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新成果失败: {str(e)}")

@router.delete("/achievement/{achievement_id}")
async def delete_achievement(
    achievement_id: int,
    current_user: str = Depends(get_current_user)
):
    """删除成果（仅发布者）"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        success = delete_published_achievement(achievement_id, user['id'])
        if not success:
            raise HTTPException(status_code=403, detail="无权删除此成果或成果不存在")
        
        return {"message": "成果删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除成果失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除成果失败: {str(e)}")

# =======================
# 需求相关接口
# =======================

@router.post("/need")
async def publish_need(
    need: NeedCreate,
    current_user: str = Depends(get_current_user)
):
    """发布需求"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        if user['role'] != 'enterprise':
            raise HTTPException(status_code=403, detail="只有企业用户可以发布需求")
        
        need_id = create_published_need(user['id'], need.dict())
        return {
            "message": "需求发布成功",
            "id": need_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发布需求失败: {e}")
        raise HTTPException(status_code=500, detail=f"发布需求失败: {str(e)}")

@router.get("/needs")
async def get_needs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    industry: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """获取需求列表"""
    try:
        result = get_published_needs(
            page=page,
            page_size=page_size,
            keyword=keyword,
            industry=industry
        )
        return result
    except Exception as e:
        logger.error(f"获取需求列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取需求列表失败: {str(e)}")

@router.get("/need/{need_id}")
async def get_need_detail(
    need_id: int,
    current_user: str = Depends(get_current_user)
):
    """获取需求详情"""
    try:
        need = get_published_need_by_id(need_id)
        if not need:
            raise HTTPException(status_code=404, detail="需求不存在")
        return need
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取需求详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取需求详情失败: {str(e)}")

@router.put("/need/{need_id}")
async def update_need(
    need_id: int,
    need: NeedUpdate,
    current_user: str = Depends(get_current_user)
):
    """更新需求（仅发布者）"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 只更新提供的字段
        update_data = {k: v for k, v in need.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的字段")
        
        success = update_published_need(need_id, user['id'], update_data)
        if not success:
            raise HTTPException(status_code=403, detail="无权修改此需求或需求不存在")
        
        return {"message": "需求更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新需求失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新需求失败: {str(e)}")

@router.delete("/need/{need_id}")
async def delete_need(
    need_id: int,
    current_user: str = Depends(get_current_user)
):
    """删除需求（仅发布者）"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        success = delete_published_need(need_id, user['id'])
        if not success:
            raise HTTPException(status_code=403, detail="无权删除此需求或需求不存在")
        
        return {"message": "需求删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除需求失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除需求失败: {str(e)}")

