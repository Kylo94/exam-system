"""
认证路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr

from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.models.user import User
from app.config import settings
from app.templating import templates

router = APIRouter()


# Pydantic模型
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "student"


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """注册页面"""
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """用户登录"""
    user = await User.get_or_none(username=username)
    
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "用户名或密码错误"},
            status_code=400
        )
    
    if not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "账户已被禁用"},
            status_code=400
        )
    
    # 创建JWT令牌
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})

    # 根据角色重定向到对应页面
    if user.role == "admin":
        redirect_url = "/admin"
    elif user.role == "teacher":
        redirect_url = "/teacher"
    else:
        redirect_url = "/dashboard"

    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    return response


@router.post("/register")
async def register(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    """用户注册"""
    # 检查用户名是否存在
    if await User.get_or_none(username=username):
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "用户名已存在"},
            status_code=400
        )
    
    # 检查邮箱是否存在
    if await User.get_or_none(email=email):
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "邮箱已被注册"},
            status_code=400
        )
    
    # 创建用户
    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        role="student"
    )
    await user.save()
    
    return RedirectResponse(url="/auth/login", status_code=303)


@router.get("/logout")
async def logout():
    """用户登出"""
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, current_user: User = Depends(get_current_user)):
    """个人资料页面"""
    return templates.TemplateResponse("auth/profile.html", {
        "request": request,
        "current_user": current_user
    })


@router.post("/change-password")
async def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """修改密码"""
    if not verify_password(old_password, current_user.password_hash):
        return templates.TemplateResponse(
            "auth/profile.html",
            {"request": request, "current_user": current_user, "error": "原密码错误"},
            status_code=400
        )
    
    current_user.password_hash = get_password_hash(new_password)
    await current_user.save()
    
    return RedirectResponse(url="/auth/profile?success=1", status_code=303)
