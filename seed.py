"""初始化資料庫並建立第一個管理員帳號。
用法：python seed.py
"""
from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", full_name="系統管理員", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("已建立管理員帳號 admin / admin123")
    else:
        print("admin 帳號已存在，略過。")
