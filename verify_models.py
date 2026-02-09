#!/usr/bin/env python
"""验证数据库模型关系"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Subject, Level, Exam, Question, Submission, Answer


def verify_models():
    """验证模型关系"""
    app = create_app('development')
    
    with app.app_context():
        print("🔍 验证数据库模型关系...")
        print("-" * 50)
        
        # 1. 创建测试数据
        print("1. 创建测试数据...")
        
        # 清理现有数据
        db.drop_all()
        db.create_all()
        
        # 创建科目
        python = Subject(name="Python测试", description="Python测试科目")
        db.session.add(python)
        
        # 创建等级
        level_1 = Level(name="一级测试", description="初级测试等级")
        db.session.add(level_1)
        
        db.session.commit()
        
        print(f"   创建科目: {python.name} (ID: {python.id})")
        print(f"   创建等级: {level_1.name} (ID: {level_1.id})")
        
        # 2. 创建试卷
        print("\n2. 创建试卷...")
        exam = Exam(
            title="测试试卷",
            subject_id=python.id,
            level_id=level_1.id,
            total_points=100
        )
        db.session.add(exam)
        db.session.commit()
        
        print(f"   创建试卷: {exam.title} (ID: {exam.id})")
        print(f"   关联科目: {exam.subject.name if exam.subject else '无'}")
        print(f"   关联等级: {exam.level.name if exam.level else '无'}")
        
        # 3. 创建题目
        print("\n3. 创建题目...")
        question = Question(
            exam_id=exam.id,
            type="single_choice",
            text="测试题目：Python中用于定义类的关键字是？",
            options=[
                {"id": "A", "text": "class"},
                {"id": "B", "text": "def"},
                {"id": "C", "text": "function"},
                {"id": "D", "text": "struct"}
            ],
            correct_answer="A",
            points=10,
            order_num=1
        )
        db.session.add(question)
        db.session.commit()
        
        print(f"   创建题目: {question.text[:30]}... (ID: {question.id})")
        print(f"   关联试卷: {question.exam.title if question.exam else '无'}")
        
        # 4. 创建答题提交
        print("\n4. 创建答题提交...")
        submission = Submission(
            exam_id=exam.id,
            student_name="测试学生",
            student_id="test001",
            total_score=85.5,
            duration_seconds=1800
        )
        db.session.add(submission)
        db.session.commit()
        
        print(f"   创建提交: 学生{submission.student_name} (ID: {submission.id})")
        print(f"   关联试卷: {submission.exam.title if submission.exam else '无'}")
        
        # 5. 创建答题记录
        print("\n5. 创建答题记录...")
        answer = Answer(
            submission_id=submission.id,
            question_id=question.id,
            student_answer="A",
            score=10.0,
            is_correct=True
        )
        db.session.add(answer)
        db.session.commit()
        
        print(f"   创建答题记录: 答案{answer.student_answer} (ID: {answer.id})")
        print(f"   关联提交: {answer.submission.id if answer.submission else '无'}")
        print(f"   关联题目: {answer.question.id if answer.question else '无'}")
        
        # 6. 验证关系
        print("\n6. 验证关系完整性...")
        
        # 科目 → 试卷
        exam_count = python.exams.count()
        print(f"   科目{python.name}的试卷数量: {exam_count} (期望: 1)")
        assert exam_count == 1, "科目-试卷关系错误"
        
        # 等级 → 试卷
        exam_count = level_1.exams.count()
        print(f"   等级{level_1.name}的试卷数量: {exam_count} (期望: 1)")
        assert exam_count == 1, "等级-试卷关系错误"
        
        # 试卷 → 题目
        question_count = exam.questions.count()
        print(f"   试卷{exam.title}的题目数量: {question_count} (期望: 1)")
        assert question_count == 1, "试卷-题目关系错误"
        
        # 试卷 → 提交
        submission_count = exam.submissions.count()
        print(f"   试卷{exam.title}的提交数量: {submission_count} (期望: 1)")
        assert submission_count == 1, "试卷-提交关系错误"
        
        # 提交 → 答题记录
        answer_count = submission.answers.count()
        print(f"   提交{submission.id}的答题记录数量: {answer_count} (期望: 1)")
        assert answer_count == 1, "提交-答题记录关系错误"
        
        # 题目 → 答题记录
        answer_count = question.answers.count()
        print(f"   题目{question.id}的答题记录数量: {answer_count} (期望: 1)")
        assert answer_count == 1, "题目-答题记录关系错误"
        
        # 7. 测试级联删除
        print("\n7. 测试级联删除...")
        
        # 删除试卷（应该级联删除题目）
        exam_id = exam.id
        db.session.delete(exam)
        db.session.commit()
        
        # 检查题目是否被删除
        deleted_question = Question.query.get(question.id)
        print(f"   删除试卷后，题目{question.id}是否存在: {deleted_question is not None} (期望: False)")
        assert deleted_question is None, "试卷-题目级联删除失败"
        
        # 科目和等级应该还存在
        existing_subject = Subject.query.get(python.id)
        existing_level = Level.query.get(level_1.id)
        print(f"   科目{python.id}是否存在: {existing_subject is not None} (期望: True)")
        print(f"   等级{level_1.id}是否存在: {existing_level is not None} (期望: True)")
        
        assert existing_subject is not None, "科目不应被删除"
        assert existing_level is not None, "等级不应被删除"
        
        print("\n✅ 所有验证通过！")
        print("-" * 50)
        print("模型关系正确，级联删除功能正常。")
        
        # 清理测试数据
        db.drop_all()
        print("\n测试数据已清理。")


if __name__ == '__main__':
    try:
        verify_models()
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)