"""
发布成果与需求相关路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
import asyncio
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
from services.vector_service import get_vector_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# =======================
# 请求/响应模型
# =======================

class AchievementCreate(BaseModel):
    name: str = Field(..., max_length=200, description="成果名称")
    field: str = Field(..., max_length=100, description="技术领域")
    description: str = Field(..., max_length=2000, description="成果简介")
    application: Optional[str] = Field(None, max_length=1000, description="应用场景")
    cooperation_mode: Optional[List[str]] = None
    contact_name: str = Field(..., max_length=50, description="联系人")
    contact_phone: str = Field(..., max_length=20, description="联系电话")
    contact_email: Optional[str] = Field(None, max_length=150, description="联系邮箱")

class AchievementUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200, description="成果名称")
    field: Optional[str] = Field(None, max_length=100, description="技术领域")
    description: Optional[str] = Field(None, max_length=2000, description="成果简介")
    application: Optional[str] = Field(None, max_length=1000, description="应用场景")
    cooperation_mode: Optional[List[str]] = None
    contact_name: Optional[str] = Field(None, max_length=50, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    contact_email: Optional[str] = Field(None, max_length=150, description="联系邮箱")

class NeedCreate(BaseModel):
    title: str = Field(..., max_length=200, description="需求标题")
    industry: str = Field(..., max_length=100, description="行业领域")
    description: str = Field(..., max_length=2000, description="需求详细描述")
    urgency_level: Optional[str] = Field(None, max_length=20, description="紧急程度")
    cooperation_preference: Optional[List[str]] = None
    budget_range: Optional[str] = Field(None, max_length=50, description="预算范围")
    company_name: str = Field(..., max_length=100, description="企业名称")
    contact_name: str = Field(..., max_length=50, description="联系人")
    contact_phone: str = Field(..., max_length=20, description="联系电话")
    contact_email: Optional[str] = Field(None, max_length=150, description="联系邮箱")

class NeedUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="需求标题")
    industry: Optional[str] = Field(None, max_length=100, description="行业领域")
    description: Optional[str] = Field(None, max_length=2000, description="需求详细描述")
    urgency_level: Optional[str] = Field(None, max_length=20, description="紧急程度")
    cooperation_preference: Optional[List[str]] = None
    budget_range: Optional[str] = Field(None, max_length=50, description="预算范围")
    company_name: Optional[str] = Field(None, max_length=100, description="企业名称")
    contact_name: Optional[str] = Field(None, max_length=50, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    contact_email: Optional[str] = Field(None, max_length=150, description="联系邮箱")

# =======================
# 成果相关接口
# =======================

def _vectorize_achievement_sync(achievement_id: int, name: str, description: str, application: str = None, field: str = None):
    """同步函数：将成果向量化（在线程池中执行）"""
    try:
        vector_service = get_vector_service()
        vector_service.add_achievement(
            achievement_id=achievement_id,
            name=name,
            description=description,
            application=application,
            field=field
        )
        logger.info(f"成果 {achievement_id} 向量化完成")
    except Exception as e:
        logger.error(f"成果 {achievement_id} 向量化失败: {str(e)}")

async def _vectorize_achievement_background(achievement_id: int, name: str, description: str, application: str = None, field: str = None):
    """异步后台任务：将成果向量化（不阻塞响应，立即开始执行）"""
    try:
        # 使用 asyncio.to_thread 在线程池中执行同步的向量化操作
        # 这样可以立即开始执行，不等待响应返回
        await asyncio.to_thread(
            _vectorize_achievement_sync,
            achievement_id,
            name,
            description,
            application,
            field
        )
        logger.info(f"成果 {achievement_id} 向量化任务完成")
    except Exception as e:
        logger.error(f"成果 {achievement_id} 向量化任务失败: {str(e)}")

@router.post("/achievement")
async def publish_achievement(
    achievement: AchievementCreate,
    current_user: str = Depends(get_current_user)
):
    """发布成果（发布成功后异步向量化）"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        if user['role'] != 'researcher':
            raise HTTPException(status_code=403, detail="只有科研人员可以发布成果")
        
        achievement_id = create_published_achievement(user['id'], achievement.dict())
        
        # 立即启动异步向量化任务（不等待响应返回，立即开始执行）
        # 使用 asyncio.create_task 确保任务立即开始执行，而不是等待响应返回
        asyncio.create_task(
            _vectorize_achievement_background(
                achievement_id,
                achievement.name,
                achievement.description,
                achievement.application,
                achievement.field
            )
        )
        logger.info(f"成果 {achievement_id} 向量化任务已启动")
        
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

@router.get("/my-achievements")
async def get_my_achievements(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    current_user: str = Depends(get_current_user)
):
    """获取当前用户发布的成果列表"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        result = get_published_achievements(
            page=page,
            page_size=page_size,
            user_id=user['id']
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取我的成果列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取我的成果列表失败: {str(e)}")

@router.get("/my-needs")
async def get_my_needs(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    current_user: str = Depends(get_current_user)
):
    """获取当前用户发布的需求列表"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        result = get_published_needs(
            page=page,
            page_size=page_size,
            user_id=user['id']
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取我的需求列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取我的需求列表失败: {str(e)}")

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
    """更新成果（仅发布者，更新后重新向量化）"""
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
        
        # 更新后重新向量化（异步，不阻塞，立即开始执行）
        # 需要获取更新后的完整数据
        updated_achievement = get_published_achievement_by_id(achievement_id)
        if updated_achievement:
            # 先删除旧的向量（如果存在）
            try:
                vector_service = get_vector_service()
                vector_service.delete_achievement(achievement_id)
            except Exception as e:
                logger.warning(f"删除旧向量失败（可能不存在）: {str(e)}")
            
            # 立即启动异步向量化任务
            asyncio.create_task(
                _vectorize_achievement_background(
                    achievement_id,
                    updated_achievement.get('name', ''),
                    updated_achievement.get('description', ''),
                    updated_achievement.get('application'),
                    updated_achievement.get('field')
                )
            )
            logger.info(f"成果 {achievement_id} 重新向量化任务已启动")
        
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
    """删除成果（仅发布者，同时从向量库删除）"""
    try:
        user = get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        success = delete_published_achievement(achievement_id, user['id'])
        if not success:
            raise HTTPException(status_code=403, detail="无权删除此成果或成果不存在")
        
        # 从向量库删除（同步执行，因为删除操作很快）
        try:
            vector_service = get_vector_service()
            vector_service.delete_achievement(achievement_id)
        except Exception as e:
            logger.warning(f"从向量库删除成果 {achievement_id} 失败（可能不存在）: {str(e)}")
        
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

