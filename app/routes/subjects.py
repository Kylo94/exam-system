"""科目路由"""

from flask import Blueprint, request, jsonify
from flask.views import MethodView

from app.services import SubjectService
from .base import BaseResource


class SubjectResource(BaseResource):
    """科目资源"""
    
    service_class = SubjectService
    
    def get(self, subject_id=None):
        """获取科目
        
        GET /api/subjects - 获取所有科目
        GET /api/subjects/<id> - 获取指定科目
        """
        try:
            if subject_id is None:
                # 获取所有科目
                params = self.parse_query_params()
                
                # 构建过滤条件
                filters = {}
                if 'search' in params:
                    filters['name'] = params['search']
                
                if 'is_active' in params:
                    filters['is_active'] = params['is_active'].lower() == 'true'
                
                # 获取数据
                subjects = self.get_service().search_subjects(
                    name=filters.get('name'),
                    is_active=filters.get('is_active'),
                    skip=params['skip'],
                    limit=params['limit']
                )
                
                # 统计总数
                total = self.get_service().count(filters)
                
                # 转换数据
                items = [self._serialize_subject(subject) for subject in subjects]
                
                return self.paginated_response(
                    items=items,
                    total=total,
                    page=params['page'],
                    per_page=params['per_page']
                )
            else:
                # 获取单个科目
                subject = self.get_service().get_by_id(subject_id)
                if not subject:
                    from app.utils.error_handlers import NotFoundError
                    raise NotFoundError(f"科目ID {subject_id} 不存在")
                
                return self.success_response(self._serialize_subject(subject))
                
        except Exception as e:
            return self.handle_exception(e)
    
    def post(self):
        """创建科目
        
        POST /api/subjects - 创建新科目
        """
        try:
            data = self.parse_request_json(['name'])
            
            subject = self.get_service().create_subject(
                name=data['name'],
                description=data.get('description', ''),
                is_active=data.get('is_active', True),
                order_index=data.get('order_index', 0)
            )
            
            return self.success_response(
                self._serialize_subject(subject),
                "科目创建成功",
                201
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def put(self, subject_id):
        """更新科目
        
        PUT /api/subjects/<id> - 更新科目
        """
        try:
            data = self.parse_request_json()
            
            subject = self.get_service().update_subject(subject_id, **data)
            if not subject:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"科目ID {subject_id} 不存在")
            
            return self.success_response(
                self._serialize_subject(subject),
                "科目更新成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def delete(self, subject_id):
        """删除科目
        
        DELETE /api/subjects/<id> - 删除科目
        """
        try:
            success = self.get_service().delete(subject_id)
            if not success:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"科目ID {subject_id} 不存在")
            
            return self.success_response(
                None,
                "科目删除成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _serialize_subject(self, subject):
        """序列化科目对象
        
        Args:
            subject: 科目对象
            
        Returns:
            序列化后的字典
        """
        return {
            'id': subject.id,
            'name': subject.name,
            'description': subject.description,
            'is_active': subject.is_active,
            'order_index': subject.order_index,
            'created_at': subject.created_at.isoformat() if subject.created_at else None,
            'updated_at': subject.updated_at.isoformat() if subject.updated_at else None
        }


# 创建蓝图
subjects_bp = Blueprint('subjects', __name__)

# 创建视图
subject_view = SubjectResource.as_view('subject_api')

# 注册路由
subjects_bp.add_url_rule(
    '/subjects',
    view_func=subject_view,
    methods=['GET', 'POST']
)

subjects_bp.add_url_rule(
    '/subjects/<int:subject_id>',
    view_func=subject_view,
    methods=['GET', 'PUT', 'DELETE']
)

# 额外路由
@subjects_bp.route('/subjects/active', methods=['GET'])
def get_active_subjects():
    """获取所有活跃科目"""
    try:
        service = SubjectService(subjects_bp.app.extensions['sqlalchemy'])
        subjects = service.get_all_active()
        
        items = [{
            'id': subject.id,
            'name': subject.name,
            'description': subject.description,
            'order_index': subject.order_index
        } for subject in subjects]
        
        return jsonify({
            'success': True,
            'data': items
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400