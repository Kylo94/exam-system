"""教师路由模块

提供教师查看学生、成绩等功能。
"""

from flask import Blueprint, jsonify, render_template, request, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models.user import User
from app.models.submission import Submission
from app.models.exam import Exam
from app.models.teacher_bind_request import TeacherBindRequest
from app.utils.response_utils import api_response, error_response

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
    try:
        from app.models.subject import Subject
        from app.models.level import Level
        from app.models.question import Question

        stats = {
            'student_count': User.query.filter_by(teacher_id=current_user.id, role='student').count(),
            'submission_count': 0,  # 暂时设为0，后续优化
            'exam_count': 0,
            'subject_count': Subject.query.count(),
            'level_count': Level.query.count(),
            'question_count': Question.query.count()
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        stats = {
            'student_count': 0,
            'submission_count': 0,
            'exam_count': 0,
            'subject_count': 0,
            'level_count': 0,
            'question_count': 0
        }

    return render_template('teacher/dashboard.html', stats=stats)


@teacher_bp.route('/my-students', methods=['GET'])
@login_required
def my_students_page():
    """我的学生页面"""
    if not current_user.is_teacher():
        return jsonify({'error': '无权参与'}), 403

    return render_template('teacher/my_students.html')


@teacher_bp.route('/student-submissions', methods=['GET'])
@login_required
def student_submissions_page():
    """学生提交情况页面"""
    if not current_user.is_teacher():
        return jsonify({'error': '无权参与'}), 403

    return render_template('teacher/student_submissions.html')


@teacher_bp.route('/bind-requests', methods=['GET'])
@login_required
def bind_requests_page():
    """绑定申请页面"""
    if not current_user.is_teacher():
        return jsonify({'error': '无权参与'}), 403

    return render_template('teacher/bind_requests.html')


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


@teacher_api_bp.route('/bind-requests', methods=['GET'])
@login_required
def get_bind_requests():
    """获取教师的绑定申请列表

    Query Parameters:
        status: 申请状态（pending/approved/rejected），默认为pending

    Returns:
        绑定申请列表
    """
    if not current_user.is_teacher():
        return error_response('无权访问', 403)

    try:
        from flask import request
        status = request.args.get('status', 'pending')

        # 根据状态获取申请
        if status == 'pending':
            requests = TeacherBindRequest.get_pending_requests(teacher_id=current_user.id)
        else:
            # 获取其他状态的申请
            requests = TeacherBindRequest.query.filter_by(
                teacher_id=current_user.id,
                status=status
            ).order_by(TeacherBindRequest.created_at.desc()).all()

        result = []
        for req in requests:
            student = User.get_by_id(req.student_id)
            result.append({
                'id': req.id,
                'student_id': req.student_id,
                'student_name': student.username if student else '未知',
                'student_email': student.email if student else '',
                'message': req.message,
                'status': req.status,
                'created_at': req.created_at.isoformat() if req.created_at else None,
                'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None
            })

        return result, 200

    except Exception as e:
        return error_response(f'获取申请列表失败: {str(e)}', 500)


@teacher_api_bp.route('/bind-requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_bind_request(request_id):
    """批准绑定申请

    Args:
        request_id: 申请ID

    Returns:
        批准结果
    """
    if not current_user.is_teacher():
        return error_response('无权访问', 403)

    try:
        bind_request = TeacherBindRequest.get_by_id(request_id)
        if not bind_request:
            return error_response('申请不存在', 404)

        if bind_request.teacher_id != current_user.id:
            return error_response('无权处理此申请', 403)

        if bind_request.status != 'pending':
            return error_response('申请已处理', 400)

        if bind_request.approve(current_user.id):
            student = User.get_by_id(bind_request.student_id)
            return {
                'success': True,
                'message': f'已通过学生 {student.username if student else ""} 的绑定申请'
            }, 200
        else:
            return error_response('批准失败', 500)

    except Exception as e:
        return error_response(f'批准申请失败: {str(e)}', 500)


@teacher_api_bp.route('/bind-requests/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_bind_request(request_id):
    """拒绝绑定申请

    Args:
        request_id: 申请ID

    Request JSON:
        reason: 拒绝原因（可选）

    Returns:
        拒绝结果
    """
    if not current_user.is_teacher():
        return error_response('无权访问', 403)

    try:
        data = request.get_json() or {}
        reason = data.get('reason', '')

        bind_request = TeacherBindRequest.get_by_id(request_id)
        if not bind_request:
            return error_response('申请不存在', 404)

        if bind_request.teacher_id != current_user.id:
            return error_response('无权处理此申请', 403)

        if bind_request.status != 'pending':
            return error_response('申请已处理', 400)

        if bind_request.reject(current_user.id, reason):
            student = User.get_by_id(bind_request.student_id)
            return {
                'success': True,
                'message': f'已拒绝学生 {student.username if student else ""} 的绑定申请'
            }, 200
        else:
            return error_response('拒绝失败', 500)

    except Exception as e:
        return error_response(f'拒绝申请失败: {str(e)}', 500)


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


@teacher_api_bp.route('/submissions', methods=['GET'])
@login_required
def get_all_submissions():
    """获取所有学生的提交记录

    Returns:
        所有提交记录列表
    """
    if not current_user.is_teacher():
        return jsonify({
            'success': False,
            'message': '无权访问'
        }), 403

    try:
        import traceback

        # 获取该教师所有学生的提交记录
        students = User.query.filter_by(teacher_id=current_user.id, role='student').all()
        current_app.logger.info(f'教师 {current_user.id} 绑定的学生数量: {len(students)}')

        student_ids = [s.id for s in students]
        current_app.logger.info(f'学生ID列表: {student_ids}')

        if not student_ids:
            return jsonify({
                'success': True,
                'data': []
            })

        submissions = Submission.query.filter(Submission.user_id.in_(student_ids)).all()
        current_app.logger.info(f'找到的提交记录数量: {len(submissions)}')

        result = []
        for submission in submissions:
            try:
                student = User.get_by_id(submission.user_id)
                exam = Exam.get_by_id(submission.exam_id)

                # 安全处理日期字段
                started_at = None
                submitted_at = None

                if submission.started_at and hasattr(submission.started_at, 'isoformat'):
                    started_at = submission.started_at.isoformat()

                if submission.submitted_at and hasattr(submission.submitted_at, 'isoformat'):
                    submitted_at = submission.submitted_at.isoformat()

                result.append({
                    'id': submission.id,
                    'student_id': submission.user_id,
                    'student_name': student.username if student else '未知',
                    'exam': {
                        'id': exam.id if exam else None,
                        'title': exam.title if exam else '未知考试'
                    } if exam else None,
                    'obtained_score': submission.obtained_score,
                    'total_score': submission.total_score,
                    'is_passed': submission.is_passed,
                    'status': submission.status,
                    'started_at': started_at,
                    'submitted_at': submitted_at
                })
            except Exception as e:
                # 跳过处理失败的记录，继续处理其他记录
                current_app.logger.error(f'处理提交记录 {submission.id} 失败: {str(e)}')
                current_app.logger.error(traceback.format_exc())
                continue

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        import traceback
        current_app.logger.error(f'获取提交记录失败: {str(e)}')
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'获取提交记录失败: {str(e)}'
        }), 500


@teacher_api_bp.route('/submissions/<int:submission_id>', methods=['GET'])
@login_required
def get_submission_detail(submission_id):
    """获取提交记录详情

    Args:
        submission_id: 提交记录ID

    Returns:
        提交记录详情
    """
    if not current_user.is_teacher():
        return jsonify({
            'success': False,
            'message': '无权访问'
        }), 403

    try:
        submission = Submission.get_by_id(submission_id)
        if not submission:
            return jsonify({
                'success': False,
                'message': '提交记录不存在'
            }), 404

        # 验证学生是否属于该教师
        student = User.get_by_id(submission.user_id)
        if not student or student.teacher_id != current_user.id:
            return jsonify({
                'success': False,
                'message': '无权访问此记录'
            }), 403

        exam = Exam.get_by_id(submission.exam_id)

        result = {
            'id': submission.id,
            'student_id': submission.user_id,
            'student_name': student.username if student else '未知',
            'exam': {
                'id': exam.id if exam else None,
                'title': exam.title if exam else '未知考试'
            } if exam else None,
            'obtained_score': submission.obtained_score,
            'total_score': submission.total_score,
            'is_passed': submission.is_passed,
            'status': submission.status,
            'started_at': submission.started_at.isoformat() if submission.started_at else None,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
            'answers': [answer.to_dict() for answer in submission.answers.all()] if submission.answers else []
        }

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取详情失败: {str(e)}'
        }), 500
