"""AI配置路由"""

from flask import Blueprint, request, jsonify
from flask.views import MethodView

from app.services import AIConfigService
from .base import BaseResource


class AIConfigResource(BaseResource):
    """AI配置资源"""

    service_class = AIConfigService

    def get(self, config_id=None):
        """获取AI配置

        GET /api/ai-configs - 获取所有AI配置
        GET /api/ai-configs/<id> - 获取指定AI配置
        """
        try:
            if config_id is None:
                # 获取所有配置
                params = self.parse_query_params()

                # 构建过滤条件
                filters = {}
                if 'provider' in params:
                    filters['provider'] = params['provider']
                if 'is_active' in params:
                    filters['is_active'] = params['is_active'].lower() == 'true'
                if 'is_default' in params:
                    filters['is_default'] = params['is_default'].lower() == 'true'

                # 获取数据
                configs = self.get_service().search_ai_configs(
                    provider=filters.get('provider'),
                    is_active=filters.get('is_active'),
                    is_default=filters.get('is_default'),
                    skip=params['skip'],
                    limit=params['limit']
                )

                # 统计总数
                total = self.get_service().count(filters)

                # 转换数据（不包含API密钥）
                items = [config.to_dict() for config in configs]

                return self.paginated_response(
                    items=items,
                    total=total,
                    page=params['page'],
                    per_page=params['per_page']
                )
            else:
                # 获取单个配置
                config = self.get_service().get_by_id(config_id)
                if not config:
                    from app.utils.error_handlers import NotFoundError
                    raise NotFoundError(f"AI配置ID {config_id} 不存在")

                return self.success_response(config.to_dict_with_key())

        except Exception as e:
            return self.handle_exception(e)

    def post(self):
        """创建AI配置

        POST /api/ai-configs - 创建新AI配置
        """
        try:
            data = self.parse_request_json(['provider', 'api_key', 'api_url'])

            config = self.get_service().create_ai_config(
                provider=data['provider'],
                api_key=data['api_key'],
                api_url=data['api_url'],
                model=data.get('model', 'deepseek-chat'),
                max_tokens=data.get('max_tokens', 2000),
                temperature=data.get('temperature', 0.7),
                description=data.get('description', ''),
                is_active=data.get('is_active', True),
                is_default=data.get('is_default', False)
            )

            return self.success_response(
                config.to_dict(),
                "AI配置创建成功",
                201
            )

        except Exception as e:
            return self.handle_exception(e)

    def put(self, config_id):
        """更新AI配置

        PUT /api/ai-configs/<id> - 更新AI配置
        """
        try:
            data = self.parse_request_json()

            config = self.get_service().update_ai_config(config_id, **data)
            if not config:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"AI配置ID {config_id} 不存在")

            return self.success_response(
                config.to_dict(),
                "AI配置更新成功"
            )

        except Exception as e:
            return self.handle_exception(e)

    def delete(self, config_id):
        """删除AI配置

        DELETE /api/ai-configs/<id> - 删除AI配置
        """
        try:
            success = self.get_service().delete(config_id)
            if not success:
                from app.utils.error_handlers import NotFoundError
                raise NotFoundError(f"AI配置ID {config_id} 不存在")

            return self.success_response(
                None,
                "AI配置删除成功"
            )

        except Exception as e:
            return self.handle_exception(e)


# 创建蓝图
ai_configs_bp = Blueprint('ai_configs', __name__)

# 创建视图
ai_config_view = AIConfigResource.as_view('ai_config_api')

# 注册路由
ai_configs_bp.add_url_rule(
    '/ai-configs',
    view_func=ai_config_view,
    methods=['GET', 'POST']
)

ai_configs_bp.add_url_rule(
    '/ai-configs/<int:config_id>',
    view_func=ai_config_view,
    methods=['GET', 'PUT', 'DELETE']
)


# 额外路由
@ai_configs_bp.route('/ai-configs/active', methods=['GET'])
def get_active_ai_config():
    """获取当前激活的AI配置"""
    try:
        from app.models.ai_config import AIConfig
        config = AIConfig.get_active_provider()

        if config:
            return jsonify({
                'success': True,
                'data': config.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': '没有激活的AI配置'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@ai_configs_bp.route('/ai-configs/<int:config_id>/set-default', methods=['POST'])
def set_default_config(config_id):
    """设置默认AI配置"""
    try:
        from app.models.ai_config import AIConfig
        config = AIConfig.set_default(config_id)

        if config:
            return jsonify({
                'success': True,
                'message': '默认AI配置设置成功',
                'data': config.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': f'AI配置ID {config_id} 不存在'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@ai_configs_bp.route('/ai-configs/<int:config_id>/test', methods=['POST'])
def test_ai_config(config_id):
    """测试AI配置是否可用"""
    try:
        from app.extensions import db
        from app.models.ai_config import AIConfig
        from app.services.ai_service import get_ai_service

        config = AIConfig.query.get(config_id)
        if not config:
            return jsonify({
                'success': False,
                'message': f'AI配置ID {config_id} 不存在'
            }), 404

        # 测试AI服务
        ai_service = get_ai_service(config)

        # 发送一个简单的测试消息
        messages = [
            {"role": "user", "content": "Hello, please respond with 'OK'."}
        ]

        response = ai_service.chat(messages)

        return jsonify({
            'success': True,
            'message': 'AI配置测试成功',
            'data': {
                'response': response.get('content', ''),
                'usage': response.get('usage', {})
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'AI配置测试失败: {str(e)}'
        }), 500


@ai_configs_bp.route('/ai-configs/providers', methods=['GET'])
def get_supported_providers():
    """获取支持的AI提供商列表"""
    try:
        providers = [
            {
                'id': 'deepseek',
                'name': 'DeepSeek',
                'description': 'DeepSeek AI',
                'default_model': 'deepseek-chat',
                'default_api_url': 'https://api.deepseek.com/v1/chat/completions',
                'models': ['deepseek-chat', 'deepseek-coder']
            },
            {
                'id': 'openai',
                'name': 'OpenAI',
                'description': 'OpenAI GPT系列',
                'default_model': 'gpt-3.5-turbo',
                'default_api_url': 'https://api.openai.com/v1/chat/completions',
                'models': ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo-preview', 'gpt-4o']
            }
        ]

        return jsonify({
            'success': True,
            'data': providers
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
