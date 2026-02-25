"""答案路由"""

from flask import Blueprint, request, jsonify
from flask.views import MethodView

from app.services import AnswerService, SubmissionService, QuestionService
from .base import BaseResource


class AnswerResource(BaseResource):
    """答案资源"""
    
    service_class = AnswerService
    
    def get(self, answer_id=None):
        """获取答案
        
        GET /api/answers - 获取所有答案
        GET /api/answers/<id> - 获取指定答案
        """
        try:
            if answer_id is None:
                # 获取所有答案
                params = self.parse_query_params()
                
                # 构建过滤条件
                submission_id = request.args.get('submission_id', type=int)
                question_id = request.args.get('question_id', type=int)
                is_correct = request.args.get('is_correct', type=str)
                
                # 转换is_correct参数
                is_correct_bool = None
                if is_correct:
                    is_correct_bool = is_correct.lower() == 'true'
                
                # 获取数据
                answers = self.get_service().search_answers(
                    submission_id=submission_id,
                    question_id=question_id,
                    is_correct=is_correct_bool,
                    skip=params['skip'],
                    limit=params['limit']
                )
                
                # 转换数据
                items = [self._serialize_answer_with_details(a) for a in answers]
                
                return self.paginated_response(
                    items=items,
                    total=len(answers),
                    page=params['page'],
                    per_page=params['per_page']
                )
            else:
                # 获取单个答案
                answer = self.get_service().get_by_id(answer_id)
                if not answer:
                    from app.utils.error_handlers import NotFoundError
                    raise NotFoundError(f"答案ID {answer_id} 不存在")
                
                return self.success_response(
                    self._serialize_answer_with_details(answer, include_question_details=True)
                )
                
        except Exception as e:
            return self.handle_exception(e)
    
    def post(self):
        """创建答案
        
        POST /api/answers - 创建新答案
        """
        try:
            data = self.parse_request_json(['submission_id', 'question_id', 'user_answer'])
            
            answer = self.get_service().create_answer(
                submission_id=data['submission_id'],
                question_id=data['question_id'],
                user_answer=data['user_answer'],
                is_correct=data.get('is_correct', False),
                score=data.get('score', 0.0)
            )
            
            return self.success_response(
                self._serialize_answer_with_details(answer),
                "答案创建成功",
                201
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def put(self, answer_id):
        """更新答案
        
        PUT /api/answers/<id> - 更新答案
        """
        try:
            data = self.parse_request_json()
            
            answer = self.get_service().update_answer(answer_id, **data)
            if not answer:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"答案ID {answer_id} 不存在")
            
            return self.success_response(
                self._serialize_answer_with_details(answer),
                "答案更新成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def delete(self, answer_id):
        """删除答案
        
        DELETE /api/answers/<id> - 删除答案
        """
        try:
            success = self.get_service().delete(answer_id)
            if not success:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"答案ID {answer_id} 不存在")
            
            return self.success_response(
                None,
                "答案删除成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _serialize_answer(self, answer):
        """序列化答案对象
        
        Args:
            answer: 答案对象
            
        Returns:
            序列化后的字典
        """
        return {
            'id': answer.id,
            'submission_id': answer.submission_id,
            'question_id': answer.question_id,
            'user_answer': answer.user_answer,
            'is_correct': answer.is_correct,
            'score': answer.score,
            'created_at': answer.created_at.isoformat() if answer.created_at else None,
            'updated_at': answer.updated_at.isoformat() if answer.updated_at else None
        }
    
    def _serialize_answer_with_details(self, answer, include_question_details=False):
        """序列化答案对象及其关联信息
        
        Args:
            answer: 答案对象
            include_question_details: 是否包含问题详细选项
            
        Returns:
            序列化后的字典
        """
        result = self._serialize_answer(answer)
        
        # 获取提交记录信息
        submission_service = SubmissionService(self.get_service().db)
        submission = submission_service.get_by_id(answer.submission_id)
        if submission:
            result['submission'] = {
                'id': submission.id,
                'exam_id': submission.exam_id,
                'user_id': submission.user_id,
                'status': submission.status
            }
        
        # 获取问题信息
        question_service = QuestionService(self.get_service().db)
        question = question_service.get_by_id(answer.question_id)
        if question:
            question_data = {
                'id': question.id,
                'content': question.content,
                'type': question.type,
                'points': question.points
            }
            
            if include_question_details:
                question_detail = question_service.get_question_with_options(question.id)
                question_data['details'] = question_detail
            
            result['question'] = question_data
        
        return result


# 创建蓝图
answers_bp = Blueprint('answers', __name__)

# 创建视图
answer_view = AnswerResource.as_view('answer_api')

# 注册路由
answers_bp.add_url_rule(
    '/answers',
    view_func=answer_view,
    methods=['GET', 'POST']
)

answers_bp.add_url_rule(
    '/answers/<int:answer_id>',
    view_func=answer_view,
    methods=['GET', 'PUT', 'DELETE']
)

# 额外路由
@answers_bp.route('/answers/<int:answer_id>/grade', methods=['POST'])
def grade_answer(answer_id):
    """评分答案"""
    try:
        from app.extensions import db
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '缺少评分数据'
            }), 400

        is_correct = data.get('is_correct', False)
        score = data.get('score', 0.0)

        service = AnswerService(db)
        answer = service.grade_answer(answer_id, is_correct, score)

        if not answer:
            return jsonify({
                'success': False,
                'message': f"答案ID {answer_id} 不存在"
            }), 404

        return jsonify({
            'success': True,
            'data': {
                'id': answer.id,
                'is_correct': answer.is_correct,
                'score': answer.score
            },
            'message': '答案评分成功'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@answers_bp.route('/questions/<int:question_id>/statistics', methods=['GET'])
def get_question_answer_statistics(question_id):
    """获取问题答案统计"""
    try:
        from app.extensions import db
        service = AnswerService(db)
        stats = service.get_answer_statistics(question_id)

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400