"""
用户认证相关路由
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import hashlib
import jwt
from datetime import datetime, timedelta
import os
from database.database import get_user_by_username, get_user_by_email, create_user

router = APIRouter()
security = HTTPBearer(auto_error=False)  # 允许可选认证

# JWT配置
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 开发模式：允许跳过认证
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict):
    """创建访问令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="无效的认证凭据")

def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    可选认证：开发模式下允许跳过认证
    生产环境请使用 get_current_user
    """
    if DEBUG_MODE:
        # 开发模式：如果没有提供 token，返回默认用户
        if credentials and credentials.credentials:
            try:
                return get_current_user(credentials)
            except:
                pass
        return "debug_user"
    else:
        # 生产模式：必须认证
        if not credentials or not credentials.credentials:
            raise HTTPException(status_code=401, detail="需要认证")
        return get_current_user(credentials)

@router.post("/register", response_model=Token)
async def register(user_data: UserRegister):
    """用户注册"""
    # 检查用户名是否已存在
    if get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 检查邮箱是否已存在
    if get_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="邮箱已存在")
    
    # 创建用户
    password_hash = hash_password(user_data.password)
    user_id = create_user(user_data.username, user_data.email, password_hash)
    
    # 创建访问令牌
    access_token = create_access_token(data={"sub": user_data.username})
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """用户登录"""
    user = get_user_by_username(user_data.username)
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """获取当前用户信息"""
    user = get_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "created_at": user["created_at"]
    }
