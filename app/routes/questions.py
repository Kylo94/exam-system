"""问题路由"""

from flask import Blueprint, request, jsonify
from flask.views import MethodView

from app.services import QuestionService, ExamService
from .base import BaseResource


class QuestionResource(BaseResource):
    """问题资源"""
    
    service_class = QuestionService
    
    def get(self, question_id=None):
        """获取问题
        
        GET /api/questions - 获取所有问题
        GET /api/questions/<id> - 获取指定问题
        """
        try:
            if question_id is None:
                # 获取所有问题
                params = self.parse_query_params()
                
                # 构建过滤条件
                exam_id = request.args.get('exam_id', type=int)
                question_type = request.args.get('type')
                content_search = request.args.get('content')
                
                # 获取数据
                questions = self.get_service().search_questions(
                    exam_id=exam_id,
                    content=content_search,
                    question_type=question_type,
                    skip=params['skip'],
                    limit=params['limit']
                )
                
                # 统计总数
                total = self.get_service().count()
                
                # 转换数据
                items = [self._serialize_question_with_exam(q) for q in questions]
                
                return self.paginated_response(
                    items=items,
                    total=total,
                    page=params['page'],
                    per_page=params['per_page']
                )
            else:
                # 获取单个问题
                question = self.get_service().get_by_id(question_id)
                if not question:
                    from app.utils.error_handlers import NotFoundError
                    raise NotFoundError(f"问题ID {question_id} 不存在")
                
                return self.success_response(
                    self._serialize_question_with_exam(question, include_details=True)
                )
                
        except Exception as e:
            return self.handle_exception(e)
    
    def post(self):
        """创建问题
        
        POST /api/questions - 创建新问题
        """
        try:
            data = self.parse_request_json(['exam_id', 'content', 'type'])
            
            # 根据类型调用不同的创建方法
            q_type = data['type']
            
            if q_type == 'single_choice':
                question = self.get_service().create_single_choice(
                    exam_id=data['exam_id'],
                    content=data['content'],
                    choices=data.get('choices', []),
                    correct_choice=data.get('correct_answer', ''),
                    score=data.get('score', 1.0),
                    explanation=data.get('explanation', ''),
                    order_index=data.get('order_index', 0)
                )
            elif q_type == 'multiple_choice':
                question = self.get_service().create_multiple_choice(
                    exam_id=data['exam_id'],
                    content=data['content'],
                    choices=data.get('choices', []),
                    correct_choices=data.get('correct_answer', []),
                    score=data.get('score', 1.0),
                    explanation=data.get('explanation', ''),
                    order_index=data.get('order_index', 0)
                )
            elif q_type == 'true_false':
                question = self.get_service().create_true_false(
                    exam_id=data['exam_id'],
                    content=data['content'],
                    is_true=data.get('correct_answer', True),
                    score=data.get('score', 1.0),
                    explanation=data.get('explanation', ''),
                    order_index=data.get('order_index', 0)
                )
            elif q_type == 'fill_blank':
                question = self.get_service().create_fill_blank(
                    exam_id=data['exam_id'],
                    content=data['content'],
                    correct_answer=data.get('correct_answer', ''),
                    score=data.get('score', 1.0),
                    explanation=data.get('explanation', ''),
                    order_index=data.get('order_index', 0)
                )
            elif q_type == 'short_answer':
                question = self.get_service().create_short_answer(
                    exam_id=data['exam_id'],
                    content=data['content'],
                    correct_answer=data.get('correct_answer', ''),
                    score=data.get('score', 1.0),
                    explanation=data.get('explanation', ''),
                    order_index=data.get('order_index', 0)
                )
            else:
                # 使用通用创建方法
                question = self.get_service().create_question(
                    exam_id=data['exam_id'],
                    content=data['content'],
                    question_type=data['type'],
                    score=data.get('score', 1.0),
                    options=data.get('options'),
                    correct_answer=data.get('correct_answer'),
                    explanation=data.get('explanation', ''),
                    order_index=data.get('order_index', 0)
                )
            
            return self.success_response(
                self._serialize_question_with_exam(question),
                "问题创建成功",
                201
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def put(self, question_id):
        """更新问题
        
        PUT /api/questions/<id> - 更新问题
        """
        try:
            data = self.parse_request_json()
            
            question = self.get_service().update_question(question_id, **data)
            if not question:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"问题ID {question_id} 不存在")
            
            return self.success_response(
                self._serialize_question_with_exam(question),
                "问题更新成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def delete(self, question_id):
        """删除问题
        
        DELETE /api/questions/<id> - 删除问题
        """
        try:
            success = self.get_service().delete(question_id)
            if not success:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"问题ID {question_id} 不存在")
            
            return self.success_response(
                None,
                "问题删除成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _serialize_question(self, question):
        """序列化问题对象

        Args:
            question: 问题对象

        Returns:
            序列化后的字典
        """
        return {
            'id': question.id,
            'exam_id': question.exam_id,
            'content': question.content,
            'type': question.type,
            'points': question.points,
            'options': question.options,
            'correct_answer': question.correct_answer,
            'explanation': question.explanation,
            'order_index': question.order_index,
            'created_at': question.created_at.isoformat() if question.created_at else None,
            'updated_at': question.updated_at.isoformat() if question.updated_at else None
        }
    
    def _serialize_question_with_exam(self, question, include_details=False):
        """序列化问题对象及其关联信息
        
        Args:
            question: 问题对象
            include_details: 是否包含详细选项和解析后的答案
            
        Returns:
            序列化后的字典
        """
        result = self._serialize_question(question)
        
        # 获取考试信息
        exam_service = ExamService(self.get_service().db)
        exam = exam_service.get_by_id(question.exam_id)
        if exam:
            result['exam'] = {
                'id': exam.id,
                'title': exam.title,
                'subject_id': exam.subject_id,
                'level_id': exam.level_id
            }
        
        # 包含详细选项和解析后的答案
        if include_details:
            question_detail = self.get_service().get_question_with_options(question.id)
            result['details'] = question_detail
        
        return result


# 创建蓝图
questions_bp = Blueprint('questions', __name__)

# 创建视图
question_view = QuestionResource.as_view('question_api')

# 注册路由
questions_bp.add_url_rule(
    '/questions',
    view_func=question_view,
    methods=['GET', 'POST']
)

questions_bp.add_url_rule(
    '/questions/<int:question_id>',
    view_func=question_view,
    methods=['GET', 'PUT', 'DELETE']
)

# 额外路由
@questions_bp.route('/questions/<int:question_id>/validate', methods=['POST'])
def validate_answer(question_id):
    """验证问题答案"""
    try:
        from app.extensions import db
        data = request.get_json()
        if not data or 'answer' not in data:
            return jsonify({
                'success': False,
                'message': '缺少答案数据'
            }), 400

        service = QuestionService(db)
        result = service.validate_answer(question_id, data['answer'])

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@questions_bp.route('/questions/exam/<int:exam_id>', methods=['GET'])
def get_questions_by_exam(exam_id):
    """获取指定考试的所有问题"""
    try:
        from app.extensions import db
        service = QuestionService(db)
        questions = service.get_by_exam_id(exam_id)

        items = [{
            'id': q.id,
            'content': q.content,
            'type': q.type,
            'points': q.points,
            'order_index': q.order_index
        } for q in questions]

        return jsonify({
            'success': True,
            'data': items
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@questions_bp.route('/questions/types', methods=['GET'])
def get_question_types():
    """获取支持的问题类型"""
    types = [
        {'value': 'single_choice', 'label': '单选题', 'description': '只有一个正确答案的选择题'},
        {'value': 'multiple_choice', 'label': '多选题', 'description': '有多个正确答案的选择题'},
        {'value': 'true_false', 'label': '判断题', 'description': '判断对错的问题'},
        {'value': 'fill_blank', 'label': '填空题', 'description': '填写空白处的问题'},
        {'value': 'short_answer', 'label': '简答题', 'description': '需要简短回答的问题'}
    ]

    return jsonify({
        'success': True,
        'data': types
    })


@questions_bp.route('/questions/practice', methods=['GET'])
def get_practice_questions():
    """获取专项刷题题目"""
    try:
        from app.extensions import db
        from app.models import Question, Exam

        # 获取筛选条件
        subject_id = request.args.get('subject_id', type=int)
        level_id = request.args.get('level_id', type=int)
        knowledge_point_id = request.args.get('knowledge_point_id', type=int)

        if not subject_id or not level_id or not knowledge_point_id:
            return jsonify({
                'success': False,
                'message': '请提供科目、难度和考点参数'
            }), 400

        # 查询符合条件考试的题目
        exams = Exam.query.filter_by(
            subject_id=subject_id,
            level_id=level_id,
            is_active=True
        ).all()

        if not exams:
            return jsonify({
                'success': False,
                'message': '没有找到符合条件的考试'
            }), 404

        exam_ids = [exam.id for exam in exams]

        # 查询题目
        questions = Question.query.filter(
            Question.exam_id.in_(exam_ids),
            Question.knowledge_point_id == knowledge_point_id
        ).order_by(Question.order_index).all()

        # 序列化题目
        items = []
        for q in questions:
            item = {
                'id': q.id,
                'exam_id': q.exam_id,
                'content': q.content,
                'type': q.type,
                'points': q.points,
                'order_index': q.order_index,
                'knowledge_point_id': q.knowledge_point_id,
                'knowledge_point_name': q.knowledge_point.name if q.knowledge_point else None
            }

            # 添加选项（如果有）
            if q.options:
                item['options'] = q.options

            # 添加考试标题
            exam = Exam.query.get(q.exam_id)
            if exam:
                item['exam_title'] = exam.title

            items.append(item)

        return jsonify({
            'success': True,
            'data': {
                'questions': items,
                'total': len(items)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400