import os

basedir = os.path.abspath(os.path.dirname(__file__))

# 開發用預設值；生產環境必須以 SECRET_KEY 環境變數覆蓋
DEFAULT_SECRET_KEY = "dev-secret-change-me"


class Config:
    # 生產環境請用環境變數覆蓋此值（create_app 會在 production 檢查）
    SECRET_KEY = os.environ.get("SECRET_KEY") or DEFAULT_SECRET_KEY
    # 未來要換 PostgreSQL 只需設定 DATABASE_URL 環境變數
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "sqlite:///" + os.path.join(basedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 附件上傳設定（可用環境變數 UPLOAD_FOLDER 覆蓋，便於指向 NAS 掛載目錄）
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or \
        os.path.join(os.path.dirname(basedir), "uploads")
    ALLOWED_EXTENSIONS = {
        "pdf", "png", "jpg", "jpeg", "gif", "doc", "docx",
        "xls", "xlsx", "ppt", "pptx", "txt", "csv", "zip",
        "dwg", "step", "stp",
    }
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
