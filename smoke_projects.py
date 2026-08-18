"""專案管理模組冒煙測試。"""
from app import create_app
from app.models import Project, db

app = create_app()

with app.test_client() as client:
    # 登入 admin
    client.post("/login", data={"username": "admin", "password": "admin123"})

    before = Project.query.count()

    # 1) 新增專案
    r = client.post("/projects/new", data={
        "name": "測試專案A", "description": "smoke test",
        "status": "active", "budget": "100000",
    }, follow_redirects=True)
    assert r.status_code == 200, f"new project {r.status_code}"
    after = Project.query.count()
    assert after == before + 1, f"project not created: {before}->{after}"
    p = Project.query.order_by(Project.id.desc()).first()
    assert p.code.startswith("PRJ-"), f"bad code {p.code}"
    print(f"[OK] 新增專案成功 {p.code} / 名稱={p.name} / 預算={p.budget}")

    # 2) 列表頁含該專案
    r = client.get("/projects", follow_redirects=True)
    assert r.status_code == 200
    assert p.name.encode("utf-8") in r.data, "list missing project"
    print("[OK] 列表頁顯示專案")

    # 3) 詳情頁含統計區
    r = client.get(f"/projects/{p.id}")
    assert r.status_code == 200
    assert "採購預估".encode("utf-8") in r.data, "detail missing stats"
    print("[OK] 詳情頁含採購/請款統計")

    # 4) 結案
    r = client.post(f"/projects/{p.id}/close", follow_redirects=True)
    assert r.status_code == 200
    from app.models import Project as P2
    assert P2.query.get(p.id).status == "closed", "close failed"
    print("[OK] 專案結案成功")

print("\n=== 專案管理模組冒煙測試全部通過 ===")
