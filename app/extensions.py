"""Flask扩展初始化"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# 数据库扩展
db = SQLAlchemy()
migrate = Migrate()

# 其他扩展可以在这里初始化
# 例如：login_manager = LoginManager()
#       cache = Cache()
#       mail = Mail()