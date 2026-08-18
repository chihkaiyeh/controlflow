"""本地預演 CI：隔離 DB，先 seed 再跑 5 個 smoke（模擬 GitHub Actions 共用 DB）。"""
import os
import sys

# 隔離 DB 路徑（Windows 正確格式）
db_path = os.path.abspath("ci_preview.db").replace("\\", "/")
os.environ["DATABASE_URL"] = "sqlite:///" + db_path
os.environ["SECRET_KEY"] = "ci-secret-key"

from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    from app.models import User
    if not User.query.filter_by(username="admin").first():
        u = User(username="admin", full_name="系統管理員", role="admin")
        u.set_password("admin123")
        db.session.add(u); db.session.commit()
        print("seed OK")

# 依序執行 5 個測試腳本（與 CI 相同順序，共用同一 DB）
tests = ["smoke.py", "smoke_projects.py", "smoke_procurements.py",
         "smoke_payments.py", "smoke_projects_v2.py"]
for t in tests:
    print(f"\n===== {t} =====")
    # 用 subprocess 跑，確保各自獨立 interpreter 但共用 DB
    rc = os.system(f"python {t}")
    if rc != 0:
        print(f"!!! {t} 失敗 (rc={rc})")
        sys.exit(1)

print("\n>>> 本地預演全部通過")
os.remove(db_path)
print("已清理 ci_preview.db")
