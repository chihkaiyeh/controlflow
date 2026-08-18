"""專案擴充 + 成員管理 整合冒煙測試。"""
from io import BytesIO

from app import create_app
from app.models import Project, ProjectAttachment, User, db

app = create_app()


def login(client, u, p):
    return client.post("/login", data={"username": u, "password": p},
                       follow_redirects=True)


with app.test_client() as client:
    login(client, "admin", "admin123")

    # 1) 新增專案（含新欄位）
    r = client.post("/projects/new", data={
        "name": "擴充測試專案", "description": "d",
        "status": "active", "priority": "high",
        "start_date": "2026-09-01", "due_date": "2026-12-31",
        "risk_assessment": "時程緊", "stakeholders": "客戶A\n內部RD",
        "target_quality": "良率95%", "budget": "200000",
    }, follow_redirects=True)
    assert r.status_code == 200, f"new {r.status_code}"
    p = Project.query.order_by(Project.id.desc()).first()
    assert p.priority == "high" and str(p.start_date) == "2026-09-01"
    assert p.stakeholders == "客戶A\n內部RD", "stakeholders 沒存好"
    assert p.target_quality == "良率95%"
    print(f"[OK] 專案新增含新欄位 {p.code} (high, 2026-09-01~2026-12-31)")

    # 2) 編輯：改優先級為 low、加風險
    r = client.post(f"/projects/{p.id}/edit", data={
        "name": p.name, "status": "active", "priority": "low",
        "start_date": "2026-09-01", "due_date": "2026-12-31",
        "risk_assessment": "已緩解", "stakeholders": p.stakeholders,
        "target_quality": p.target_quality, "budget": "200000"},
        follow_redirects=True)
    assert Project.query.get(p.id).priority == "low"
    print("[OK] 編輯成功：優先級 low")

    # 3) 附件上傳
    data = {"file": (BytesIO(b"hello attachment"), "test.txt")}
    r = client.post(f"/projects/{p.id}/upload", data=data,
                    content_type="multipart/form-data", follow_redirects=True)
    assert r.status_code == 200
    att = ProjectAttachment.query.filter_by(project_id=p.id).first()
    assert att and att.original_name == "test.txt"
    print(f"[OK] 附件上傳成功 {att.original_name} ({att.size} bytes)")

    # 4) 附件下載
    r = client.get(f"/projects/{p.id}/attachment/{att.id}")
    assert r.status_code == 200 and r.data == b"hello attachment"
    print("[OK] 附件下載內容正確")

    # 5) 成員新增
    r = client.post("/users/new", data={
        "username": "mem1", "full_name": "成員一", "password": "mem123",
        "role": "employee"}, follow_redirects=True)
    assert r.status_code == 200
    u = User.query.filter_by(username="mem1").first()
    assert u and u.role == "employee"
    print("[OK] 新增成員 mem1 (employee)")

    # 6) 改角色為 finance
    r = client.post(f"/users/{u.id}/role", data={"role": "finance"},
                    follow_redirects=True)
    assert User.query.get(u.id).role == "finance"
    print("[OK] 成員角色改為 finance")

    # 7) 停用
    r = client.post(f"/users/{u.id}/toggle", follow_redirects=True)
    assert User.query.get(u.id).active is False
    print("[OK] 成員停用")

print("\n=== 專案擴充 + 成員管理 冒煙測試全部通過 ===")
