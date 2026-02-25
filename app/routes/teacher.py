"""教师路由模块

提供教师查看学生、成绩等功能。
"""

from flask import Blueprint, jsonify, render_template
from flask_login import login_required, current_user

from app.extensions import db
from app.models.user import User
from app.models.submission import Submission
from app.models.exam import Exam

teacher_bp = Blueprint('teacher', __name__)

# 教师API蓝图
teacher_api_bp = Blueprint('teacher_api', __name__, url_prefix='/api/teacher')


@teacher_bp.route('/dashboard')
@login_required
def dashboard():
    """教师仪表板"""
    if not current_user.is_teacher():
        return jsonify({'error': '无权访问'}), 403
    
    # 统计信息
    from app.models.subject import Subject
    from app.models.level import Level
    from app.models.question import Question
    
    stats = {
        'student_count': User.query.filter_by(teacher_id=current_user.id, role='student').count(),
        'submission_count': Submission.query.join(User).filter(User.teacher_id == current_user.id).count(),
        'exam_count': 0,  # 暂时设置为0，Exam模型暂无created_by字段
        'subject_count': Subject.query.count(),
        'level_count': Level.query.count(),
        'question_count': Question.query.count()
    }
    
    return render_template('teacher/dashboard.html', stats=stats)


@teacher_bp.route('/my-students', methods=['GET'])
@login_required
def my_students_page():
    """我的学生页面"""
    if not current_user.is_teacher():
        return jsonify({'error': '无权参与'}), 403
    
    return render_template('teacher/my_students.html')


@teacher_api_bp.route('/students', methods=['GET'])
@login_required
def get_my_students():
    """获取教师的学生列表
    
    Returns:
        学生列表及统计信息
    """
    if not current_user.is_teacher():
        return jsonify({
            'success': False,
            'message': '无权访问'
        }), 403
    
    try:
        # 获取所有绑定到该教师的学生
        students = User.query.filter_by(teacher_id=current_user.id, role='student').all()
        
        result = []
        for student in students:
            # 获取学生的考试统计
            submissions = Submission.query.filter_by(user_id=student.id).all()
            completed = [s for s in submissions if s.status in ['submitted', 'graded']]
            passed = [s for s in completed if s.is_passed]
            
            pass_rate = (len(passed) / len(completed) * 100) if completed else 0
            
            result.append({
                'id': student.id,
                'username': student.username,
                'email': student.email,
                'created_at': student.created_at.isoformat() if student.created_at else None,
                'submission_count': len(submissions),
                'completed_count': len(completed),
                'passed_count': len(passed),
                'pass_rate': round(pass_rate, 2)
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取学生列表失败: {str(e)}'
        }), 500


@teacher_api_bp.route('/students/<int:student_id>/submissions', methods=['GET'])
@login_required
def get_student_submissions(student_id):
    """获取指定学生的考试记录
    
    Args:
        student_id: 学生ID
        
    Returns:
        考试记录列表
    """
    if not current_user.is_teacher():
        return jsonify({
            'success': False,
            'message': '无权访问'
        }), 403
    
    try:
        # 验证学生是否属于该教师
        student = User.get_by_id(student_id)
        if not student or student.teacher_id != current_user.id:
            return jsonify({
                'success': False,
                'message': '学生不存在或不属于您'
            }), 404
        
        # 获取学生的考试记录
        submissions = Submission.query.filter_by(user_id=student_id).all()
        
        result = []
        for submission in submissions:
            exam = Exam.get_by_id(submission.exam_id)
            
            result.append({
                'id': submission.id,
                'exam': {
                    'id': exam.id if exam else None,
                    'title': exam.title if exam else '未知考试'
                } if exam else None,
                'obtained_score': submission.obtained_score,
                'total_score': submission.total_score,
                'is_passed': submission.is_passed,
                'status': submission.status,
                'started_at': submission.started_at.isoformat() if submission.started_at else None,
                'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取考试记录失败: {str(e)}'
        }), 500
