"""初始化資料庫並建立第一個管理員帳號。

用法（密碼由環境變數提供，不接受寫死的預設密碼）：
    ADMIN_PASSWORD='你的強密碼' python seed.py

生產模式請同時設定 SECRET_KEY，否則 create_app() 會拒絕啟動。
"""
import os

from app import create_app, db
from app.models import User

MIN_PASSWORD_LENGTH = 10


def main():
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        raise SystemExit(
            "錯誤：請先設定 ADMIN_PASSWORD 環境變數後再執行 seed.py。"
        )
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(
            f"錯誤：ADMIN_PASSWORD 至少需要 {MIN_PASSWORD_LENGTH} 個字元。"
        )

    app = create_app()
    with app.app_context():
        db.create_all()
        if User.query.filter_by(username="admin").first():
            print("admin 帳號已存在，略過。")
            return
        admin = User(username="admin", full_name="系統管理員", role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print("已建立管理員帳號 admin（密碼取自 ADMIN_PASSWORD）。")


if __name__ == "__main__":
    main()
