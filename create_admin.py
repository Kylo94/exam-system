#!/usr/bin/env python
"""创建管理员用户脚本"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User


def create_admin_user():
    """创建管理员用户"""
    # 使用环境变量或默认为 production
    env = os.environ.get('FLASK_ENV', 'production')
    app = create_app(env)
    
    with app.app_context():
        print("🔧 正在检查管理员用户...")
        
        # 检查是否已存在管理员用户
        existing_admin = User.get_by_username('admin')
        if existing_admin:
            print(f"⚠️  管理员用户 'admin' 已存在 (ID: {existing_admin.id})")
            print(f"   角色: {existing_admin.role}")
            print(f"   邮箱: {existing_admin.email}")
            return
        
        # 检查邮箱是否已被占用
        existing_email = User.get_by_email('admin@example.com')
        if existing_email:
            print(f"⚠️  邮箱 'admin@example.com' 已被用户 '{existing_email.username}' 占用")
            print("   将使用备用邮箱 'admin@system.local'")
            email = 'admin@system.local'
        else:
            email = 'admin@example.com'
        
        try:
            # 创建管理员用户
            admin = User(
                username='admin',
                email=email,
                password='admin',
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            
            print(f"✅ 管理员用户创建成功!")
            print(f"   用户名: admin")
            print(f"   密码: admin")
            print(f"   邮箱: {email}")
            print(f"   角色: admin")
            print("\n⚠️  安全提示:")
            print("   1. 首次登录后请立即修改密码")
            print("   2. 建议更改邮箱地址为有效邮箱")
            print("   3. 定期更换密码以确保账户安全")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 创建管理员用户失败: {str(e)}")
            sys.exit(1)


if __name__ == '__main__':
    create_admin_user()