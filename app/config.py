import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 生產環境請用環境變數覆蓋此值
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-me"
    # 未來要換 PostgreSQL 只需設定 DATABASE_URL 環境變數
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "sqlite:///" + os.path.join(basedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 附件上傳設定
    UPLOAD_FOLDER = os.path.join(os.path.dirname(basedir), "uploads")
    ALLOWED_EXTENSIONS = {
        "pdf", "png", "jpg", "jpeg", "gif", "doc", "docx",
        "xls", "xlsx", "ppt", "pptx", "txt", "csv", "zip",
        "dwg", "step", "stp",
    }
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
