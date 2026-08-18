import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

from .config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "請先登入"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import auth_bp
    from .main import main_bp
    from .projects import projects_bp
    from .procurements import proc_bp
    from .payments import pay_bp
    from .inventory import inv_bp
    from .users import users_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix="/projects")
    app.register_blueprint(proc_bp, url_prefix="/procurements")
    app.register_blueprint(pay_bp, url_prefix="/payments")
    app.register_blueprint(inv_bp, url_prefix="/inventory")
    app.register_blueprint(users_bp, url_prefix="/users")

    # 確保附件上傳目錄存在
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # 確保模型已載入後再建表
    from . import models  # noqa: F401
    with app.app_context():
        db.create_all()

    return app
