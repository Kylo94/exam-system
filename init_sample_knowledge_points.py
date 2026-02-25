"""初始化示例考点数据"""

from app import create_app
from app.extensions import db
from app.models import Subject, Level, KnowledgePoint

def init_sample_knowledge_points():
    """初始化示例考点数据"""
    app = create_app()

    with app.app_context():
        # 获取科目和难度数据
        subjects = Subject.query.all()
        levels = Level.query.all()

        if not subjects:
            print("错误：没有找到科目数据，请先创建科目")
            return

        if not levels:
            print("错误：没有找到难度数据，请先创建难度")
            return

        # 清空现有考点数据
        KnowledgePoint.query.delete()
        db.session.commit()

        # 创建示例考点数据
        sample_data = [
            # 编程基础相关考点
            {
                'name': 'Python基础语法',
                'code': 'python-basic-01',
                'subject': subjects[0].name if subjects else None,
                'level': levels[0].name if len(levels) > 0 else None,
                'description': 'Python变量、数据类型、运算符等基础知识'
            },
            {
                'name': '流程控制',
                'code': 'python-basic-02',
                'subject': subjects[0].name if subjects else None,
                'level': levels[0].name if len(levels) > 0 else None,
                'description': 'if语句、循环语句、分支结构'
            },
            {
                'name': '函数定义与调用',
                'code': 'python-basic-03',
                'subject': subjects[0].name if subjects else None,
                'level': levels[1].name if len(levels) > 1 else None,
                'description': '函数定义、参数传递、返回值'
            },
            {
                'name': '类与对象',
                'code': 'python-oop-01',
                'subject': subjects[0].name if subjects else None,
                'level': levels[2].name if len(levels) > 2 else None,
                'description': '类定义、实例化、属性和方法'
            },
            {
                'name': '继承与多态',
                'code': 'python-oop-02',
                'subject': subjects[0].name if subjects else None,
                'level': levels[2].name if len(levels) > 2 else None,
                'description': '类的继承、多态、抽象类'
            },
        ]

        # 查找科目和难度ID
        subject_map = {s.name: s.id for s in subjects}
        level_map = {l.name: l.id for l in levels}

        # 创建考点
        created_count = 0
        for data in sample_data:
            subject_id = subject_map.get(data['subject'])
            level_id = level_map.get(data['level'])

            if not subject_id:
                print(f"跳过：找不到科目 '{data['subject']}'")
                continue

            kp = KnowledgePoint(
                name=data['name'],
                code=data['code'],
                subject_id=subject_id,
                level_id=level_id,
                description=data['description'],
                order_index=created_count + 1,
                is_active=True
            )

            db.session.add(kp)
            created_count += 1
            print(f"创建考点: {data['name']} ({data['code']})")

        db.session.commit()
        print(f"\n成功创建 {created_count} 个考点")

if __name__ == '__main__':
    init_sample_knowledge_points()
