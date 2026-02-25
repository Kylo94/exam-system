#!/usr/bin/env python
"""数据库初始化脚本"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Subject, Level, Exam, Question, Submission, Answer


def init_database():
    """初始化数据库"""
    app = create_app('development')
    
    with app.app_context():
        # 创建所有表
        print("创建数据库表...")
        db.create_all()
        
        # 创建示例数据
        print("创建示例数据...")
        create_sample_data()
        
        print("数据库初始化完成！")


def create_sample_data():
    """创建示例数据"""
    
    # 检查是否已有数据
    if Subject.query.first() is not None:
        print("数据库中已有数据，跳过示例数据创建")
        return
    
    # 创建科目
    python_subject = Subject(name="Python", description="Python编程语言")
    java_subject = Subject(name="Java", description="Java编程语言")
    cpp_subject = Subject(name="C++", description="C++编程语言")

    db.session.add_all([python_subject, java_subject, cpp_subject])
    db.session.commit()

    # 创建等级
    level_1 = Level(name="一级", subject_id=python_subject.id, description="初级水平")
    level_2 = Level(name="二级", subject_id=python_subject.id, description="中级水平")
    level_3 = Level(name="三级", subject_id=python_subject.id, description="高级水平")

    db.session.add_all([level_1, level_2, level_3])
    
    # 创建试卷
    exam = Exam(
        title="Python二级考试真题",
        subject_id=python_subject.id,
        level_id=level_2.id,
        total_points=100,
        file_path="案例题目/202403Python二级真题(带答案解析).docx"
    )
    
    db.session.add(exam)
    db.session.commit()
    
    # 创建题目
    question1 = Question(
        exam_id=exam.id,
        type="single_choice",
        content="Python中用于定义类的关键字是？",
        options=[
            {"id": "A", "text": "class"},
            {"id": "B", "text": "def"},
            {"id": "C", "text": "function"},
            {"id": "D", "text": "struct"}
        ],
        correct_answer="A",
        points=10,
        order_index=1
    )

    question2 = Question(
        exam_id=exam.id,
        type="judgment",
        content="Python是静态类型语言。",
        correct_answer="错误",
        points=10,
        order_index=2
    )

    question3 = Question(
        exam_id=exam.id,
        type="fill_blank",
        content="Python中用于打印输出的函数是______。",
        correct_answer="print",
        points=10,
        order_index=3
    )
    
    db.session.add_all([question1, question2, question3])
    
    # 更新试卷统计
    exam.question_count = 3
    exam.has_images = False
    db.session.commit()
    
    print(f"创建示例数据：")
    print(f"  - 科目：{python_subject.name}, {java_subject.name}, {cpp_subject.name}")
    print(f"  - 等级：{level_1.name}, {level_2.name}, {level_3.name}")
    print(f"  - 试卷：{exam.title}")
    print(f"  - 题目：3道")


def clear_database():
    """清空数据库"""
    app = create_app('development')
    
    with app.app_context():
        print("警告：这将删除所有数据！")
        confirm = input("确认删除所有数据？(输入 'yes' 继续): ")
        
        if confirm.lower() == 'yes':
            # 删除所有表（注意：SQLite不支持DROP ALL，需要逐个删除）
            db.drop_all()
            print("所有表已删除")
        else:
            print("操作已取消")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--clear':
        clear_database()
    else:
        init_database()