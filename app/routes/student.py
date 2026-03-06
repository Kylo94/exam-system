"""学生专用路由 - 专项刷题功能"""

import random
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from app.models import Subject, Level, KnowledgePoint, Question, Exam, Submission
from app.extensions import db

student_bp = Blueprint('student', __name__)


@student_bp.route('/practice/create', methods=['POST'])
@login_required
def create_practice_exam():
    """创建专项刷题临时试卷"""
    try:
        data = request.get_json()
        subject_id = data.get('subject_id')
        level_id = data.get('level_id')
        knowledge_point_id = data.get('knowledge_point_id')
        question_count = data.get('question_count')

        # 验证必填字段
        if not all([subject_id, level_id, knowledge_point_id]):
            return jsonify({
                'success': False,
                'message': '请选择科目、难度和考点'
            }), 400

        # 获取符合筛选条件的题目（通过关联的exam获取subject_id和level_id）
        query = Question.query.join(Exam).filter(
            Exam.subject_id == subject_id,
            Exam.level_id == level_id,
            Question.knowledge_point_id == knowledge_point_id
        )

        all_questions = query.all()

        if not all_questions:
            return jsonify({
                'success': False,
                'message': '该考点下暂无可用题目'
            }), 400

        # 确定题目数量
        available_count = len(all_questions)
        requested_count = question_count

        if requested_count is None or requested_count > available_count:
            # 要求的题目数量大于可用数量，使用全部可用题目
            selected_questions = all_questions
            actual_count = available_count
            use_all = True
        else:
            # 随机抽取指定数量的题目
            selected_questions = random.sample(all_questions, requested_count)
            actual_count = requested_count
            use_all = False

        # 创建临时试卷
        current_app.logger.info(f"为用户 {current_user.id} 创建临时刷题试卷，题目数量: {question_count}")

        # 获取科目和难度信息
        subject = Subject.query.get(subject_id)
        level = Level.query.get(level_id)
        kp = KnowledgePoint.query.get(knowledge_point_id)

        # 构建试卷标题
        exam_title = f"{subject.name if subject else ''} - {level.name if level else ''} - {kp.name if kp else ''} - 专项练习"

        # 计算总分
        total_points = sum(q.points for q in selected_questions)

        # 设置时间范围（练习试卷设置一个很长的有效时间）
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(days=365)  # 一年有效期

        # 创建临时试卷（标记为临时类型）
        exam = Exam(
            title=exam_title,
            subject_id=subject_id,
            level_id=level_id,
            is_temporary=True,  # 标记为临时试卷
            description=f"专项练习：{kp.name if kp else ''}",
            total_points=total_points,
            duration_minutes=None,  # 刷题不限时
            is_active=True,
            max_attempts=None,  # 不限次数
            pass_score=60.0,
            start_time=start_time,
            end_time=end_time
        )

        # 设置题目数量（通过属性赋值）
        exam.question_count = len(selected_questions)
        exam.has_images = any(q.has_image for q in selected_questions)

        db.session.add(exam)
        db.session.flush()  # 获取 exam.id

        # 为临时试卷创建题目关联（不创建新题目副本，只建立引用关系）
        from app.models.exam_question import ExamQuestion

        for idx, q in enumerate(selected_questions):
            # 创建考试-题目关联记录
            exam_question = ExamQuestion(
                exam_id=exam.id,
                question_id=q.id,
                order_index=idx,
                points=q.points  # 可以覆盖原题目的分值
            )
            db.session.add(exam_question)

        db.session.commit()
        current_app.logger.info(f"临时试卷创建成功，ID: {exam.id}, 题目数量: {len(selected_questions)}")

        # 构建返回消息
        if use_all:
            message = f'练习试卷创建成功（该考点共{actual_count}道题，已全部包含）'
        else:
            message = f'练习试卷创建成功（{actual_count}道题）'

        return jsonify({
            'success': True,
            'message': message,
            'data': {
                'exam_id': exam.id,
                'exam_title': exam.title,
                'question_count': len(selected_questions),
                'requested_count': requested_count,
                'available_count': available_count
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建练习试卷失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'创建练习试卷失败: {str(e)}'
        }), 500
