import os

from flask import Flask, flash, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError

from .config import Config, DEFAULT_SECRET_KEY

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = "auth.login"
login_manager.login_message = "請先登入"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if (os.environ.get("FLASK_ENV") == "production"
            and app.config["SECRET_KEY"] == DEFAULT_SECRET_KEY):
        raise RuntimeError(
            "生產模式必須設定 SECRET_KEY 環境變數（不可使用開發預設值）。"
        )

    # 全站 CSRF 保護：所有 POST 都必須帶 csrf_token
    csrf.init_app(app)

    db.init_app(app)
    login_manager.init_app(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        flash("表單已過期或無效，請重新整理頁面後再試。", "danger")
        # 只接受本站 referrer，避免被當成開放式重新導向
        ref = request.referrer or ""
        if not ref.startswith(request.host_url):
            ref = url_for("main.dashboard")
        return redirect(ref)

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
