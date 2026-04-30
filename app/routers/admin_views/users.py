"""管理员 - 用户管理"""
from fastapi import APIRouter, Depends, Request, HTTPException, Form

from app.auth import require_admin
from app.models.user import User
from app.services.user_service import UserService
from app.templating import templates

router = APIRouter()


@router.get("/users", response_class=None)
async def admin_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    role: str = None,
    search: str = None,
    current_user: User = Depends(require_admin)
):
    """用户列表"""
    users, total = await UserService.list_users(role=role, search=search, page=page, page_size=page_size)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "current_user": current_user,
        "users": users,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        },
        "filters": {"role": role, "search": search}
    })


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: int, current_user: User = Depends(require_admin)):
    """切换用户激活状态"""
    try:
        user = await UserService.toggle_active(user_id, current_user.id)
        return {"success": True, "is_active": user.is_active}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/change-role")
async def change_user_role(user_id: int, role: str, current_user: User = Depends(require_admin)):
    """修改用户角色"""
    try:
        await UserService.change_role(user_id, role)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/create")
async def create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("student")
):
    """创建用户"""
    try:
        user = await UserService.create_user(username, email, password, role)
        return {"success": True, "id": user.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))