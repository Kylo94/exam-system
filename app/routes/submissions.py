"""考试提交路由"""

from flask import Blueprint, request, jsonify
from flask.views import MethodView
from flask_login import current_user

from app.services import SubmissionService, ExamService
from .base import BaseResource


class SubmissionResource(BaseResource):
    """考试提交资源"""
    
    service_class = SubmissionService
    
    def get(self, submission_id=None):
        """获取提交记录

        GET /api/submissions - 获取所有提交记录
        GET /api/submissions/<id> - 获取指定提交记录
        """
        try:
            if submission_id is None:
                # 获取所有提交记录
                params = self.parse_query_params()

                # 构建过滤条件
                exam_id = request.args.get('exam_id', type=int)
                user_id = request.args.get('user_id', type=int)
                status = request.args.get('status')

                # 如果没有指定user_id，且当前用户已登录，则默认只查看自己的记录
                # 管理员和教师可以查看所有记录（需要检查权限）
                if user_id is None and current_user.is_authenticated:
                    # 检查当前用户是否为管理员或教师
                    from app.models import User
                    user = User.query.get(current_user.id)
                    if user and user.role in ['admin', 'teacher']:
                        # 管理员和教师可以查看所有记录，不需要user_id过滤
                        pass
                    else:
                        # 普通用户只能查看自己的记录
                        user_id = current_user.id

                # 获取数据
                if exam_id and user_id:
                    submissions = self.get_service().get_user_exam_submissions(user_id, exam_id)
                elif exam_id:
                    # 如果指定了exam_id但没有user_id，需要检查权限
                    # 管理员和教师可以查看某次考试的所有记录
                    from app.models import User
                    user = User.query.get(current_user.id)
                    if user and user.role in ['admin', 'teacher']:
                        submissions = self.get_service().get_by_exam_id(exam_id)
                    else:
                        # 普通用户需要user_id过滤
                        submissions = self.get_service().get_user_exam_submissions(current_user.id, exam_id)
                elif user_id:
                    submissions = self.get_service().get_by_user_id(user_id)
                else:
                    submissions = self.get_service().get_all(
                        skip=params['skip'],
                        limit=params['limit']
                    )

                # 转换数据
                items = [self._serialize_submission_with_exam(s) for s in submissions]

                return self.paginated_response(
                    items=items,
                    total=len(submissions),
                    page=params['page'],
                    per_page=params['per_page']
                )
            else:
                # 获取单个提交记录
                submission = self.get_service().get_by_id(submission_id)
                if not submission:
                    from app.utils.error_handlers import NotFoundError
                    raise NotFoundError(f"提交记录ID {submission_id} 不存在")

                # 权限检查：只有管理员、教师或记录的所有者可以查看
                from app.models import User
                user = User.query.get(current_user.id)
                if user and user.role not in ['admin', 'teacher']:
                    # 普通用户只能查看自己的记录
                    if submission.user_id != current_user.id:
                        from app.utils.error_handlers import ForbiddenError
                        raise ForbiddenError("您没有权限查看此记录")

                # 获取详细数据
                details = self.get_service().get_submission_details(submission_id)

                return self.success_response(details)

        except Exception as e:
            return self.handle_exception(e)
    
    def post(self):
        """创建提交记录
        
        POST /api/submissions - 创建新提交记录
        """
        try:
            data = self.parse_request_json(['exam_id', 'user_id'])
            
            submission = self.get_service().create_submission(
                exam_id=data['exam_id'],
                user_id=data['user_id'],
                started_at=data.get('started_at'),
                submitted_at=data.get('submitted_at')
            )
            
            return self.success_response(
                self._serialize_submission_with_exam(submission),
                "提交记录创建成功",
                201
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def put(self, submission_id):
        """更新提交记录
        
        PUT /api/submissions/<id> - 更新提交记录
        """
        try:
            data = self.parse_request_json()
            
            submission = self.get_service().update_submission(submission_id, **data)
            if not submission:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"提交记录ID {submission_id} 不存在")
            
            return self.success_response(
                self._serialize_submission_with_exam(submission),
                "提交记录更新成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def delete(self, submission_id):
        """删除提交记录
        
        DELETE /api/submissions/<id> - 删除提交记录
        """
        try:
            success = self.get_service().delete(submission_id)
            if not success:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"提交记录ID {submission_id} 不存在")
            
            return self.success_response(
                None,
                "提交记录删除成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _serialize_submission(self, submission):
        """序列化提交记录对象
        
        Args:
            submission: 提交记录对象
            
        Returns:
            序列化后的字典
        """
        return {
            'id': submission.id,
            'exam_id': submission.exam_id,
            'user_id': submission.user_id,
            'started_at': submission.started_at.isoformat() if submission.started_at else None,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
            'status': submission.status,
            'total_score': submission.total_score,
            'obtained_score': submission.obtained_score,
            'score_percentage': submission.score_percentage,
            'is_passed': submission.is_passed,
            'created_at': submission.created_at.isoformat() if submission.created_at else None,
            'updated_at': submission.updated_at.isoformat() if submission.updated_at else None
        }
    
    def _serialize_submission_with_exam(self, submission):
        """序列化提交记录对象及其关联信息
        
        Args:
            submission: 提交记录对象
            
        Returns:
            序列化后的字典
        """
        result = self._serialize_submission(submission)
        
        # 获取考试信息
        exam_service = ExamService(self.get_service().db)
        exam = exam_service.get_by_id(submission.exam_id)
        if exam:
            result['exam'] = {
                'id': exam.id,
                'title': exam.title,
                'subject_id': exam.subject_id,
                'level_id': exam.level_id,
                'pass_score': exam.pass_score
            }
        
        return result


# 创建蓝图
submissions_bp = Blueprint('submissions', __name__)

# 创建视图
submission_view = SubmissionResource.as_view('submission_api')

# 注册路由
submissions_bp.add_url_rule(
    '/submissions',
    view_func=submission_view,
    methods=['GET', 'POST']
)

submissions_bp.add_url_rule(
    '/submissions/<int:submission_id>',
    view_func=submission_view,
    methods=['GET', 'PUT', 'DELETE']
)

# 额外路由
@submissions_bp.route('/submissions/<int:submission_id>/submit', methods=['POST'])
def submit_exam(submission_id):
    """提交考试答案"""
    try:
        from app.extensions import db
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({
                'success': False,
                'message': '缺少答案数据'
            }), 400

        service = SubmissionService(db)
        result = service.submit_exam(submission_id, data['answers'])

        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': '考试提交成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': result['error']
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@submissions_bp.route('/submissions/<int:submission_id>/answers', methods=['GET'])
def get_submission_answers(submission_id):
    """获取提交的答案"""
    try:
        from app.extensions import db
        service = SubmissionService(db)
        answers = service.get_by_submission_id(submission_id)

        items = [{
            'id': a.id,
            'question_id': a.question_id,
            'user_answer': a.user_answer,
            'is_correct': a.is_correct,
            'score': a.score,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in answers]

        return jsonify({
            'success': True,
            'data': items
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@submissions_bp.route('/exams/<int:exam_id>/statistics', methods=['GET'])
def get_exam_submission_statistics(exam_id):
    """获取考试提交统计"""
    try:
        from app.extensions import db
        service = SubmissionService(db)
        stats = service.calculate_statistics(exam_id)

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@submissions_bp.route('/exams/<int:exam_id>/can_start', methods=['GET'])
def can_start_exam(exam_id):
    """检查是否可以开始考试"""
    try:
        from app.extensions import db
        user_id = request.args.get('user_id', type=int)

        service = ExamService(db)
        result = service.can_start_exam(exam_id, user_id)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400