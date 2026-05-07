"""管理员 - 用户管理"""
from fastapi import APIRouter, Depends, Form, HTTPException, Request

from app.auth import require_admin
from app.models.audit_log import AuditLog
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
async def toggle_user_active(request: Request, user_id: int, current_user: User = Depends(require_admin)):
    """切换用户激活状态"""
    client_ip = request.client.host if request.client else None
    try:
        user = await UserService.toggle_active(user_id, current_user.id)
        # 审计日志
        await AuditLog.log_update(
            user=current_user,
            resource_type="user",
            resource_id=user_id,
            description=f"切换用户 {user.username} 激活状态: {'启用' if user.is_active else '禁用'}",
            ip_address=client_ip,
            status="success"
        )
        return {"success": True, "is_active": user.is_active}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/change-role")
async def change_user_role(request: Request, user_id: int, role: str, current_user: User = Depends(require_admin)):
    """修改用户角色"""
    client_ip = request.client.host if request.client else None
    try:
        target_user = await User.get_or_none(id=user_id)
        old_role = target_user.role if target_user else "unknown"
        await UserService.change_role(user_id, role)
        # 审计日志
        await AuditLog.log_update(
            user=current_user,
            resource_type="user",
            resource_id=user_id,
            description=f"修改用户角色: {target_user.username} 从 {old_role} 改为 {role}",
            ip_address=client_ip,
            status="success"
        )
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
    client_ip = request.client.host if request.client else None
    try:
        user = await UserService.create_user(username, email, password, role)
        # 审计日志
        await AuditLog.log_create(
            user=user,
            resource_type="user",
            resource_id=user.id,
            description=f"管理员创建用户: {username} (角色: {role})",
            ip_address=client_ip,
            status="success"
        )
        return {"success": True, "id": user.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/delete")
async def delete_user(request: Request, user_id: int, current_user: User = Depends(require_admin)):
    """删除用户"""
    client_ip = request.client.host if request.client else None
    try:
        target_user = await User.get_or_none(id=user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if target_user.id == current_user.id:
            raise HTTPException(status_code=400, detail="不能删除自己")

        await UserService.delete_user(user_id)
        # 审计日志
        await AuditLog.log_delete(
            user=current_user,
            resource_type="user",
            resource_id=user_id,
            description=f"删除用户: {target_user.username} (角色: {target_user.role})",
            ip_address=client_ip,
            status="success"
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
