"""科目路由"""

from flask import Blueprint, request, jsonify
from flask.views import MethodView

from app.services import SubjectService, LevelService
from app.models import Level
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
                is_active=bool(data.get('is_active', True)),
                order_index=int(data.get('order_index', 0))
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
        include_levels = request.args.get('include_levels', '').lower() == 'true'
        data = {
            'id': subject.id,
            'name': subject.name,
            'description': subject.description,
            'is_active': subject.is_active,
            'order_index': subject.order_index,
            'created_at': subject.created_at.isoformat() if subject.created_at else None,
            'updated_at': subject.updated_at.isoformat() if subject.updated_at else None
        }

        if include_levels:
            levels = Level.query.filter_by(subject_id=subject.id).order_by(Level.order_index).all()
            data['levels'] = [{
                'id': level.id,
                'name': level.name,
                'description': level.description,
                'is_active': level.is_active,
                'order_index': level.order_index
            } for level in levels]

        return data


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
        from app.extensions import db
        service = SubjectService(db)
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


# ===== 等级管理路由 =====

@subjects_bp.route('/subjects/<int:subject_id>/levels', methods=['GET'])
def get_subject_levels(subject_id):
    """获取指定科目的所有等级"""
    try:
        from app.models import Subject
        subject = Subject.query.get(subject_id)
        if not subject:
            return jsonify({
                'success': False,
                'message': f'科目ID {subject_id} 不存在'
            }), 404

        params = request.args
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 10))
        skip = (page - 1) * per_page

        # 获取等级
        query = Level.query.filter_by(subject_id=subject_id).order_by(Level.order_index)
        total = query.count()
        levels = query.offset(skip).limit(per_page).all()

        items = [{
            'id': level.id,
            'name': level.name,
            'description': level.description,
            'is_active': level.is_active,
            'order_index': level.order_index,
            'exam_count': level.exams.count(),
            'subject_id': level.subject_id
        } for level in levels]

        total_pages = (total + per_page - 1) // per_page

        return jsonify({
            'success': True,
            'data': {
                'items': items,
                'pagination': {
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': total_pages,
                    'has_prev': page > 1,
                    'has_next': page < total_pages
                }
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@subjects_bp.route('/subjects/<int:subject_id>/levels', methods=['POST'])
def create_subject_level(subject_id):
    """为指定科目创建等级"""
    try:
        from app.models import Subject
        subject = Subject.query.get(subject_id)
        if not subject:
            return jsonify({
                'success': False,
                'message': f'科目ID {subject_id} 不存在'
            }), 404

        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({
                'success': False,
                'message': '等级名称不能为空'
            }), 400

        # 检查是否已存在同名等级
        existing = Level.query.filter_by(subject_id=subject_id, name=name).first()
        if existing:
            return jsonify({
                'success': False,
                'message': '该科目下已存在同名等级'
            }), 400

        level = Level(
            subject_id=subject_id,
            name=name,
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
            order_index=int(data.get('order_index', 0))
        )

        from app.extensions import db
        db.session.add(level)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '等级创建成功',
            'data': {
                'id': level.id,
                'name': level.name,
                'description': level.description,
                'is_active': level.is_active,
                'order_index': level.order_index
            }
        }), 201

    except Exception as e:
        from app.extensions import db
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'创建等级失败: {str(e)}'
        }), 500


@subjects_bp.route('/subjects/<int:subject_id>/levels/<int:level_id>', methods=['GET'])
def get_subject_level(subject_id, level_id):
    """获取指定科目和等级的信息"""
    try:
        level = Level.query.filter_by(id=level_id, subject_id=subject_id).first()
        if not level:
            return jsonify({
                'success': False,
                'message': f'等级ID {level_id} 不存在或不属于该科目'
            }), 404

        return jsonify({
            'success': True,
            'data': {
                'id': level.id,
                'name': level.name,
                'description': level.description,
                'is_active': level.is_active,
                'order_index': level.order_index,
                'exam_count': level.exams.count(),
                'subject_id': level.subject_id
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@subjects_bp.route('/subjects/<int:subject_id>/levels/<int:level_id>', methods=['PUT'])
def update_subject_level(subject_id, level_id):
    """更新指定科目的等级"""
    try:
        level = Level.query.filter_by(id=level_id, subject_id=subject_id).first()
        if not level:
            return jsonify({
                'success': False,
                'message': f'等级ID {level_id} 不存在或不属于该科目'
            }), 404

        data = request.get_json()

        if 'name' in data:
            name = data['name']
            # 检查是否与其他等级重名
            existing = Level.query.filter_by(subject_id=subject_id, name=name).first()
            if existing and existing.id != level_id:
                return jsonify({
                    'success': False,
                    'message': '该科目下已存在同名等级'
                }), 400
            level.name = name

        if 'description' in data:
            level.description = data['description']
        if 'is_active' in data:
            level.is_active = data['is_active']
        if 'order_index' in data:
            level.order_index = int(data['order_index'])

        from app.extensions import db
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '等级更新成功',
            'data': {
                'id': level.id,
                'name': level.name,
                'description': level.description,
                'is_active': level.is_active,
                'order_index': level.order_index
            }
        })

    except Exception as e:
        from app.extensions import db
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新等级失败: {str(e)}'
        }), 500


@subjects_bp.route('/subjects/<int:subject_id>/levels/<int:level_id>', methods=['DELETE'])
def delete_subject_level(subject_id, level_id):
    """删除指定科目的等级"""
    try:
        level = Level.query.filter_by(id=level_id, subject_id=subject_id).first()
        if not level:
            return jsonify({
                'success': False,
                'message': f'等级ID {level_id} 不存在或不属于该科目'
            }), 404

        from app.extensions import db
        db.session.delete(level)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '等级删除成功'
        })

    except Exception as e:
        from app.extensions import db
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除等级失败: {str(e)}'
        }), 500