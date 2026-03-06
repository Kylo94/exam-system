#!/usr/bin/env python
"""测试 Waitress 启动"""

import os
from dotenv import load_dotenv

load_dotenv('.env.production')

from app import create_app
app = create_app('production')

print("=" * 50)
print("生产环境启动 (Waitress) - 测试模式")
print("=" * 50)
print(f"DEBUG: {app.config['DEBUG']}")
print(f"FLASK_PORT: {os.environ.get('FLASK_PORT', '5004')}")
print()

# 简单测试路由
@app.route('/test')
def test():
    return {'status': 'ok', 'message': 'Waitress is working!'}

if __name__ == '__main__':
    from waitress import serve
    try:
        serve(
            app,
            host='0.0.0.0',
            port=int(os.environ.get('FLASK_PORT', '5004')),
            threads=4,
            url_prefix='',
        )
    except KeyboardInterrupt:
        print("\n服务已停止")
