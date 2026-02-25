"""创建知识点表"""

from app import create_app
from app.extensions import db

def init_knowledge_points():
    """初始化考点数据"""
    app = create_app()

    with app.app_context():
        # 删除表（如果存在）
        db.drop_all()
        db.create_all()

        print("数据库表创建完成！")

if __name__ == '__main__':
    init_knowledge_points()
