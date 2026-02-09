"""Flask扩展初始化"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# 数据库扩展
db = SQLAlchemy()
migrate = Migrate()

# 认证扩展
login_manager = LoginManager()

# 其他扩展可以在这里初始化
# 例如：cache = Cache()
#       mail = Mail()