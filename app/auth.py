"""
认证模块 - JWT + Passlib
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.models.user import User

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_token_from_cookie(request: Request) -> Optional[str]:
    """从Cookie获取token"""
    return request.cookies.get("access_token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> User:
    """获取当前用户（必须登录）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 优先从Cookie获取token
    if not token:
        token = get_token_from_cookie(request)

    if not token:
        raise credentials_exception

    user = await _get_user_from_token(token)
    if user is None:
        raise credentials_exception

    return user


async def get_optional_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> Optional[User]:
    """获取当前用户（可选，未登录返回None）"""
    # 优先从Cookie获取token
    if not token:
        token = get_token_from_cookie(request)

    if not token:
        return None

    return await _get_user_from_token(token)


async def _get_user_from_token(token: str) -> Optional[User]:
    """从token获取用户"""
    payload = decode_token(token)
    if payload is None:
        return None

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        return None

    user = await User.get_or_none(id=int(user_id_str))
    if user is None or not user.is_active:
        return None

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user


def require_role(*roles: str):
    """角色依赖装饰器"""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此资源"
            )
        return current_user
    return role_checker


# 常用角色依赖
require_admin = require_role("admin")
require_teacher = require_role("teacher")
require_admin_or_teacher = require_role("admin", "teacher")
require_student = require_role("student")
