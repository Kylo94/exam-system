"""考点管理路由"""

from flask import Blueprint, jsonify, request
from app.routes.base import BaseResource
from app.services.knowledge_point_service import KnowledgePointService

knowledge_points_bp = Blueprint('knowledge_points', __name__)


class KnowledgePointResource(BaseResource):
    """考点资源"""

    def get_service(self):
        """获取考点服务"""
        from app.extensions import db
        return KnowledgePointService(db)

    def _serialize_knowledge_point(self, knowledge_point):
        """序列化考点对象"""
        data = {
            'id': knowledge_point.id,
            'name': knowledge_point.name,
            'code': knowledge_point.code,
            'subject_id': knowledge_point.subject_id,
            'level_id': knowledge_point.level_id,
            'description': knowledge_point.description,
            'parent_id': knowledge_point.parent_id,
            'order_index': knowledge_point.order_index,
            'is_active': knowledge_point.is_active,
            'created_at': knowledge_point.created_at.isoformat() if knowledge_point.created_at else None,
            'updated_at': knowledge_point.updated_at.isoformat() if knowledge_point.updated_at else None
        }

        # 添加关联信息
        if knowledge_point.subject:
            data['subject_name'] = knowledge_point.subject.name
        if knowledge_point.level:
            data['level_name'] = knowledge_point.level.name
        if knowledge_point.parent:
            data['parent_name'] = knowledge_point.parent.name

        return data


@knowledge_points_bp.route('/knowledge-points', methods=['GET', 'POST'])
def knowledge_points_list():
    """考点列表和创建"""
    service = KnowledgePointResource()

    if request.method == 'POST':
        # 创建考点
        data = request.get_json()

        # 验证必填字段
        required_fields = ['name', 'code', 'subject_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'缺少必填字段: {field}'
                }), 400

        # 检查代码是否重复
        from app.models import KnowledgePoint
        existing = KnowledgePoint.query.filter_by(code=data['code']).first()
        if existing:
            return jsonify({
                'success': False,
                'message': '考点代码已存在'
            }), 400

        try:
            knowledge_point = service.get_service().create(data)
            return jsonify({
                'success': True,
                'data': service._serialize_knowledge_point(knowledge_point),
                'message': '考点创建成功'
            }), 201
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400

    else:
        # 获取考点列表
        params = request.args

        # 构建过滤条件
        subject_id = params.get('subject_id')
        level_id = params.get('level_id')
        is_active = params.get('is_active')

        filters = {}
        if subject_id:
            try:
                filters['subject_id'] = int(subject_id)
            except ValueError:
                pass

        if level_id:
            try:
                filters['level_id'] = int(level_id)
            except ValueError:
                pass

        if is_active:
            filters['is_active'] = is_active.lower() == 'true'

        # 获取数据
        skip = int(params.get('skip', 0))
        limit = int(params.get('limit', 100))

        knowledge_points = service.get_service().search_knowledge_points(
            subject_id=filters.get('subject_id'),
            level_id=filters.get('level_id'),
            is_active=filters.get('is_active'),
            skip=skip,
            limit=limit
        )

        # 统计总数
        total = service.get_service().count(filters)

        # 转换数据
        items = [service._serialize_knowledge_point(kp) for kp in knowledge_points]

        return jsonify({
            'success': True,
            'data': {
                'items': items,
                'total': total,
                'skip': skip,
                'limit': limit
            }
        })


@knowledge_points_bp.route('/knowledge-points/<int:knowledge_point_id>', methods=['GET', 'PUT', 'DELETE'])
def knowledge_point_detail(knowledge_point_id):
    """考点详情"""
    service = KnowledgePointResource()

    if request.method == 'GET':
        # 获取考点详情
        knowledge_point = service.get_service().get_by_id(knowledge_point_id)
        if not knowledge_point:
            return jsonify({
                'success': False,
                'message': '考点不存在'
            }), 404

        return jsonify({
            'success': True,
            'data': service._serialize_knowledge_point(knowledge_point)
        })

    elif request.method == 'PUT':
        # 更新考点
        knowledge_point = service.get_service().get_by_id(knowledge_point_id)
        if not knowledge_point:
            return jsonify({
                'success': False,
                'message': '考点不存在'
            }), 404

        data = request.get_json()
        try:
            updated_kp = service.get_service().update(knowledge_point, data)
            return jsonify({
                'success': True,
                'data': service._serialize_knowledge_point(updated_kp),
                'message': '考点更新成功'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400

    elif request.method == 'DELETE':
        # 删除考点
        knowledge_point = service.get_service().get_by_id(knowledge_point_id)
        if not knowledge_point:
            return jsonify({
                'success': False,
                'message': '考点不存在'
            }), 404

        try:
            if service.get_service().delete(knowledge_point):
                return jsonify({
                    'success': True,
                    'message': '考点删除成功'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '删除失败'
                }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400


@knowledge_points_bp.route('/knowledge-points/by-subject/<int:subject_id>', methods=['GET'])
def knowledge_points_by_subject(subject_id):
    """根据科目获取考点列表"""
    service = KnowledgePointResource()

    knowledge_points = service.get_service().get_by_subject(subject_id)
    items = [service._serialize_knowledge_point(kp) for kp in knowledge_points]

    return jsonify({
        'success': True,
        'data': items
    })


@knowledge_points_bp.route('/knowledge-points/by-level/<int:level_id>', methods=['GET'])
def knowledge_points_by_level(level_id):
    """根据难度等级获取考点列表"""
    service = KnowledgePointResource()

    knowledge_points = service.get_service().get_by_level(level_id)
    items = [service._serialize_knowledge_point(kp) for kp in knowledge_points]

    return jsonify({
        'success': True,
        'data': items
    })


@knowledge_points_bp.route('/knowledge-points/by-subject-level/<int:subject_id>/<int:level_id>', methods=['GET'])
def knowledge_points_by_subject_level(subject_id, level_id):
    """根据科目和难度等级获取考点列表"""
    service = KnowledgePointResource()

    knowledge_points = service.get_service().get_by_subject_and_level(subject_id, level_id)
    items = [service._serialize_knowledge_point(kp) for kp in knowledge_points]

    return jsonify({
        'success': True,
        'data': items
    })
