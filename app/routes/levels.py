"""难度级别路由"""

from flask import Blueprint, request, jsonify
from flask.views import MethodView

from app.services import LevelService
from .base import BaseResource


class LevelResource(BaseResource):
    """难度级别资源"""
    
    service_class = LevelService
    
    def get(self, level_id=None):
        """获取难度级别
        
        GET /api/levels - 获取所有难度级别
        GET /api/levels/<id> - 获取指定难度级别
        """
        try:
            if level_id is None:
                # 获取所有难度级别
                params = self.parse_query_params()

                # 构建过滤条件
                filters = {}
                if 'search' in params:
                    filters['name'] = params['search']

                if 'is_active' in params:
                    filters['is_active'] = params['is_active'].lower() == 'true'

                # 获取数据
                levels = self.get_service().search_levels(
                    name=filters.get('name'),
                    is_active=filters.get('is_active'),
                    skip=params['skip'],
                    limit=params['limit']
                )

                # 统计总数
                total = self.get_service().count(filters)

                # 转换数据
                items = [self._serialize_level(level) for level in levels]

                return self.paginated_response(
                    items=items,
                    total=total,
                    page=params['page'],
                    per_page=params['per_page']
                )
            else:
                # 获取单个难度级别
                level = self.get_service().get_by_id(level_id)
                if not level:
                    from app.utils.error_handlers import NotFoundError
                    raise NotFoundError(f"难度级别ID {level_id} 不存在")
                
                return self.success_response(self._serialize_level(level))
                
        except Exception as e:
            return self.handle_exception(e)
    
    def post(self):
        """创建难度级别

        POST /api/levels - 创建新难度级别
        """
        try:
            data = self.parse_request_json(['name', 'subject_id'])

            # 获取下一个排序索引
            order_index = data.get('order_index', self.get_service().get_next_order_index())

            level = self.get_service().create({
                'name': data['name'],
                'subject_id': data['subject_id'],
                'description': data.get('description', ''),
                'is_active': data.get('is_active', True),
                'order_index': order_index
            })

            return self.success_response(
                self._serialize_level(level),
                "难度级别创建成功",
                201
            )

        except Exception as e:
            return self.handle_exception(e)
    
    def put(self, level_id):
        """更新难度级别
        
        PUT /api/levels/<id> - 更新难度级别
        """
        try:
            data = self.parse_request_json()
            
            level = self.get_service().update_level(level_id, **data)
            if not level:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"难度级别ID {level_id} 不存在")
            
            return self.success_response(
                self._serialize_level(level),
                "难度级别更新成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def delete(self, level_id):
        """删除难度级别
        
        DELETE /api/levels/<id> - 删除难度级别
        """
        try:
            success = self.get_service().delete(level_id)
            if not success:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"难度级别ID {level_id} 不存在")
            
            return self.success_response(
                None,
                "难度级别删除成功"
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _serialize_level(self, level):
        """序列化难度级别对象

        Args:
            level: 难度级别对象

        Returns:
            序列化后的字典
        """
        return {
            'id': level.id,
            'name': level.name,
            'order_index': level.order_index,
            'description': level.description,
            'is_active': level.is_active,
            'created_at': level.created_at.isoformat() if level.created_at else None,
            'updated_at': level.updated_at.isoformat() if level.updated_at else None
        }


# 创建蓝图
levels_bp = Blueprint('levels', __name__)

# 创建视图
level_view = LevelResource.as_view('level_api')

# 注册路由
levels_bp.add_url_rule(
    '/levels',
    view_func=level_view,
    methods=['GET', 'POST']
)

levels_bp.add_url_rule(
    '/levels/<int:level_id>',
    view_func=level_view,
    methods=['GET', 'PUT', 'DELETE']
)

# 额外路由
@levels_bp.route('/levels/active', methods=['GET'])
def get_active_levels():
    """获取所有活跃难度级别"""
    try:
        from app.extensions import db
        service = LevelService(db)
        levels = service.get_all_active()

        items = [{
            'id': level.id,
            'name': level.name,
            'order_index': level.order_index,
            'description': level.description
        } for level in levels]

        return jsonify({
            'success': True,
            'data': items
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@levels_bp.route('/levels/by-subject/<int:subject_id>', methods=['GET'])
def get_levels_by_subject(subject_id):
    """根据科目获取难度级别列表"""
    try:
        from app.models import Level
        levels = Level.get_by_subject(subject_id)

        items = [{
            'id': level.id,
            'name': level.name,
            'order_index': level.order_index,
            'description': level.description,
            'is_active': level.is_active
        } for level in levels]

        return jsonify({
            'success': True,
            'data': items
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400