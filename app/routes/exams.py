"""考试路由"""

from flask import Blueprint, request, jsonify
from flask.views import MethodView

from app.services import ExamService, SubjectService, LevelService
from .base import BaseResource


class ExamResource(BaseResource):
    """考试资源"""
    
    service_class = ExamService
    
    def get(self, exam_id=None):
        """获取考试
        
        GET /api/exams - 获取所有考试
        GET /api/exams/<id> - 获取指定考试
        """
        try:
            if exam_id is None:
                # 获取所有考试
                params = self.parse_query_params()
                
                # 构建过滤条件
                filters = {}
                if 'search' in params:
                    filters['title'] = params['search']
                
                if 'subject_id' in params:
                    try:
                        filters['subject_id'] = int(params['subject_id'])
                    except ValueError:
                        pass
                
                if 'level_id' in params:
                    try:
                        filters['level_id'] = int(params['level_id'])
                    except ValueError:
                        pass
                
                if 'is_active' in params:
                    filters['is_active'] = params['is_active'].lower() == 'true'
                
                # 获取数据
                exams = self.get_service().search_exams(
                    title=filters.get('title'),
                    subject_id=filters.get('subject_id'),
                    level_id=filters.get('level_id'),
                    is_active=filters.get('is_active'),
                    skip=params['skip'],
                    limit=params['limit']
                )
                
                # 统计总数
                total = self.get_service().count(filters)
                
                # 转换数据（包含关联信息）
                items = [self._serialize_exam_with_associations(exam) for exam in exams]
                
                return self.paginated_response(
                    items=items,
                    total=total,
                    page=params['page'],
                    per_page=params['per_page']
                )
            else:
                # 获取单个考试
                exam = self.get_service().get_by_id(exam_id)
                if not exam:
                    from app.utils.error_handlers import NotFoundError
                    raise NotFoundError(f"考试ID {exam_id} 不存在")
                
                return self.success_response(
                    self._serialize_exam_with_associations(exam, include_questions=True)
                )
                
        except Exception as e:
            return self.handle_exception(e)
    
    def post(self):
        """创建考试
        
        POST /api/exams - 创建新考试
        """
        try:
            data = self.parse_request_json(['title', 'subject_id', 'level_id'])
            
            exam = self.get_service().create_exam(
                title=data['title'],
                subject_id=data['subject_id'],
                level_id=data['level_id'],
                description=data.get('description', ''),
                duration_minutes=data.get('duration_minutes', 60),
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
                is_active=data.get('is_active', True),
                max_attempts=data.get('max_attempts', 1),
                pass_score=data.get('pass_score', 60.0)
            )
            
            return self.success_response(
                self._serialize_exam_with_associations(exam),
                "考试创建成功",
                201
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def put(self, exam_id):
        """更新考试
        
        PUT /api/exams/<id> - 更新考试
        """
        try:
            data = self.parse_request_json()
            
            exam = self.get_service().update_exam(exam_id, **data)
            if not exam:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"考试ID {exam_id} 不存在")
            
            return self.success_response(
                self._serialize_exam_with_associations(exam),
                "考试更新成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def delete(self, exam_id):
        """删除考试
        
        DELETE /api/exams/<id> - 删除考试
        """
        try:
            success = self.get_service().delete(exam_id)
            if not success:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"考试ID {exam_id} 不存在")
            
            return self.success_response(
                None,
                "考试删除成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _serialize_exam(self, exam):
        """序列化考试对象
        
        Args:
            exam: 考试对象
            
        Returns:
            序列化后的字典
        """
        return {
            'id': exam.id,
            'title': exam.title,
            'description': exam.description,
            'subject_id': exam.subject_id,
            'level_id': exam.level_id,
            'duration_minutes': exam.duration_minutes,
            'start_time': exam.start_time.isoformat() if exam.start_time else None,
            'end_time': exam.end_time.isoformat() if exam.end_time else None,
            'is_active': exam.is_active,
            'max_attempts': exam.max_attempts,
            'pass_score': exam.pass_score,
            'created_at': exam.created_at.isoformat() if exam.created_at else None,
            'updated_at': exam.updated_at.isoformat() if exam.updated_at else None
        }
    
    def _serialize_exam_with_associations(self, exam, include_questions=False):
        """序列化考试对象及其关联信息
        
        Args:
            exam: 考试对象
            include_questions: 是否包含问题列表
            
        Returns:
            序列化后的字典
        """
        result = self._serialize_exam(exam)
        
        # 获取科目信息
        subject_service = SubjectService(self.get_service().db)
        subject = subject_service.get_by_id(exam.subject_id)
        if subject:
            result['subject'] = {
                'id': subject.id,
                'name': subject.name,
                'description': subject.description
            }
        
        # 获取难度级别信息
        level_service = LevelService(self.get_service().db)
        level = level_service.get_by_id(exam.level_id)
        if level:
            result['level'] = {
                'id': level.id,
                'name': level.name,
                'difficulty': level.difficulty,
                'description': level.description
            }
        
        # 获取问题统计
        from app.services import QuestionService
        question_service = QuestionService(self.get_service().db)
        questions = question_service.get_by_exam_id(exam.id)
        result['question_count'] = len(questions)
        result['total_score'] = sum(q.score for q in questions)
        
        # 包含问题列表
        if include_questions:
            result['questions'] = [
                self._serialize_question(q) for q in questions
            ]
        
        # 考试状态
        status = self.get_service().get_exam_status(exam.id)
        result['status'] = {
            'is_upcoming': status['is_upcoming'],
            'is_ongoing': status['is_ongoing'],
            'is_completed': status['is_completed'],
            'has_started': status['has_started'],
            'has_ended': status['has_ended'],
            'time_remaining': str(status['time_remaining']) if status['time_remaining'] else None
        }
        
        return result
    
    def _serialize_question(self, question):
        """序列化问题对象
        
        Args:
            question: 问题对象
            
        Returns:
            序列化后的字典
        """
        return {
            'id': question.id,
            'content': question.content,
            'type': question.type,
            'score': question.score,
            'options': question.options,
            'explanation': question.explanation,
            'order_index': question.order_index
        }


# 创建蓝图
exams_bp = Blueprint('exams', __name__)

# 创建视图
exam_view = ExamResource.as_view('exam_api')

# 注册路由
exams_bp.add_url_rule(
    '/exams',
    view_func=exam_view,
    methods=['GET', 'POST']
)

exams_bp.add_url_rule(
    '/exams/<int:exam_id>',
    view_func=exam_view,
    methods=['GET', 'PUT', 'DELETE']
)

# 额外路由
@exams_bp.route('/exams/active', methods=['GET'])
def get_active_exams():
    """获取所有活跃考试"""
    try:
        service = ExamService(exams_bp.app.extensions['sqlalchemy'])
        exams = service.get_active_exams()
        
        items = [{
            'id': exam.id,
            'title': exam.title,
            'description': exam.description,
            'subject_id': exam.subject_id,
            'level_id': exam.level_id,
            'duration_minutes': exam.duration_minutes
        } for exam in exams]
        
        return jsonify({
            'success': True,
            'data': items
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@exams_bp.route('/exams/upcoming', methods=['GET'])
def get_upcoming_exams():
    """获取即将开始的考试"""
    try:
        service = ExamService(exams_bp.app.extensions['sqlalchemy'])
        exams = service.get_upcoming_exams()
        
        items = [{
            'id': exam.id,
            'title': exam.title,
            'description': exam.description,
            'subject_id': exam.subject_id,
            'level_id': exam.level_id,
            'duration_minutes': exam.duration_minutes,
            'start_time': exam.start_time.isoformat() if exam.start_time else None,
            'end_time': exam.end_time.isoformat() if exam.end_time else None
        } for exam in exams]
        
        return jsonify({
            'success': True,
            'data': items
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@exams_bp.route('/exams/ongoing', methods=['GET'])
def get_ongoing_exams():
    """获取进行中的考试"""
    try:
        service = ExamService(exams_bp.app.extensions['sqlalchemy'])
        exams = service.get_ongoing_exams()
        
        items = [{
            'id': exam.id,
            'title': exam.title,
            'description': exam.description,
            'subject_id': exam.subject_id,
            'level_id': exam.level_id,
            'duration_minutes': exam.duration_minutes,
            'start_time': exam.start_time.isoformat() if exam.start_time else None,
            'end_time': exam.end_time.isoformat() if exam.end_time else None
        } for exam in exams]
        
        return jsonify({
            'success': True,
            'data': items
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@exams_bp.route('/exams/completed', methods=['GET'])
def get_completed_exams():
    """获取已结束的考试"""
    try:
        service = ExamService(exams_bp.app.extensions['sqlalchemy'])
        exams = service.get_completed_exams()
        
        items = [{
            'id': exam.id,
            'title': exam.title,
            'description': exam.description,
            'subject_id': exam.subject_id,
            'level_id': exam.level_id,
            'duration_minutes': exam.duration_minutes,
            'start_time': exam.start_time.isoformat() if exam.start_time else None,
            'end_time': exam.end_time.isoformat() if exam.end_time else None
        } for exam in exams]
        
        return jsonify({
            'success': True,
            'data': items
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@exams_bp.route('/exams/<int:exam_id>/status', methods=['GET'])
def get_exam_status(exam_id):
    """获取考试状态"""
    try:
        service = ExamService(exams_bp.app.extensions['sqlalchemy'])
        status = service.get_exam_status(exam_id)
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@exams_bp.route('/exams/<int:exam_id>/statistics', methods=['GET'])
def get_exam_statistics(exam_id):
    """获取考试统计数据"""
    try:
        service = ExamService(exams_bp.app.extensions['sqlalchemy'])
        stats = service.get_exam_statistics(exam_id)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400