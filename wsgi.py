"""生产环境WSGI入口文件"""

import os
from app import create_app
from config import config

# 获取环境配置
env = os.environ.get('FLASK_ENV', 'production')
app = create_app(env)

if __name__ == '__main__':
    app.run()