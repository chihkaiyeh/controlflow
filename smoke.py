"""基礎架構冒煙測試：建立 app、確認路由與資料表、確認 admin 可登入。"""
from app import create_app
from app.models import User, db

app = create_app()

with app.test_client() as client:
    # 1) 登入頁可訪問
    r = client.get("/login")
    assert r.status_code == 200, f"login page {r.status_code}"
    print("[OK] GET /login ->", r.status_code)

    # 2) 未登入訪問受保護頁會被導向 login
    r = client.get("/")
    assert r.status_code in (302, 401), f"protected {r.status_code}"
    print("[OK] GET / (未登入) 被擋 ->", r.status_code)

    # 3) 用 admin 登入
    r = client.post("/login", data={"username": "admin", "password": "admin123"},
                    follow_redirects=True)
    assert r.status_code == 200, f"login post {r.status_code}"
    # 登入成功並保持 session：再訪問受保護首頁應回 200（不再被 302 擋掉）
    r2 = client.get("/")
    assert r2.status_code == 200, f"after-login GET / -> {r2.status_code}"
    assert "儀表板" in r2.data.decode("utf-8"), "dashboard content missing"
    print("[OK] admin 登入成功，session 保持，進入儀表板")

    # 4) 登入後可看儀表板與四個模組頁（目前為 placeholder）
    for path in ["/", "/projects", "/procurements", "/payments", "/inventory"]:
        r = client.get(path, follow_redirects=True)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        print(f"[OK] GET {path} ->", r.status_code)

# 5) 資料表已建立
with app.app_context():
    from sqlalchemy import inspect
    tables = set(inspect(db.engine).get_table_names())
    expected = {"user", "project", "procurement_request",
                "payment_request", "inventory_item", "stock_movement"}
    missing = expected - set(tables)
    assert not missing, f"missing tables: {missing}"
    print("[OK] 資料表齊全:", sorted(tables))
    print("[OK] 使用者數:", User.query.count())

print("\n=== 基礎架構冒煙測試全部通過 ===")
