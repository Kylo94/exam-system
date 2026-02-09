#!/usr/bin/env python
"""应用入口文件"""

import os
from app import create_app
from config import config

# 获取环境配置
env = os.environ.get('FLASK_ENV', 'development')
# 传递配置名称字符串，而不是配置类
app = create_app(env)

if __name__ == '__main__':
    app.run(
        host=os.environ.get('FLASK_HOST', '0.0.0.0'),
        port=int(os.environ.get('FLASK_PORT', 5000)),
        debug=app.config['DEBUG']
    )