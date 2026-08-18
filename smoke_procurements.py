"""採購申請模組冒煙測試，含核准流程與權限。"""
from app import create_app
from app.models import User, Project, ProcurementRequest, db

app = create_app()

with app.app_context():
    # 確保有一個進行中的專案與一個員工帳號
    proj = Project.query.filter_by(code="PRJ-0002").first()
    if not proj:
        proj = Project(code="PRJ-TEST", name="測試專案", status="active",
                       owner_id=1, budget=100000)
        db.session.add(proj)
        db.session.commit()
    proj_id = proj.id
    emp = User.query.filter_by(username="emp1").first()
    if not emp:
        emp = User(username="emp1", full_name="員工一號", role="employee")
        emp.set_password("emp123")
        db.session.add(emp)
        db.session.commit()


def login(client, user, pw):
    client.post("/login", data={"username": user, "password": pw})


with app.test_client() as client:
    # --- 員工送出採購申請 ---
    login(client, "emp1", "emp123")
    r = client.post("/procurements/new", data={
        "project_id": str(proj_id), "item_name": "測試螺絲",
        "spec": "M3", "qty": "100", "unit": "個",
        "estimated_price": "500", "reason": "組裝用",
    }, follow_redirects=True)
    assert r.status_code == 200, f"emp new proc {r.status_code}"
    pr = ProcurementRequest.query.order_by(ProcurementRequest.id.desc()).first()
    assert pr.code.startswith("PRC-") and pr.status == "submitted"
    print(f"[OK] 員工送出採購 {pr.code}（待核准）")

    # --- 員工無權核准：直接打 approve 應被擋 ---
    r = client.post(f"/procurements/{pr.id}/approve", data={"decision": "approve"})
    assert r.status_code in (302, 403), f"emp approve not blocked: {r.status_code}"
    assert ProcurementRequest.query.get(pr.id).status == "submitted"
    print("[OK] 員工無法核准（權限隔離正常）")

    # --- admin 登入並核准 ---
    login(client, "admin", "admin123")
    r = client.post(f"/procurements/{pr.id}/approve", data={"decision": "approve"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert ProcurementRequest.query.get(pr.id).status == "approved"
    print("[OK] admin 核准成功 -> approved")

    # --- 標記已下單 ---
    r = client.post(f"/procurements/{pr.id}/ordered", follow_redirects=True)
    assert r.status_code == 200
    assert ProcurementRequest.query.get(pr.id).status == "ordered"
    print("[OK] 標記已下單 -> ordered")

print("\n=== 採購申請模組冒煙測試全部通過 ===")
