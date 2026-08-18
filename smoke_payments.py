"""請款模組冒煙測試，含核准流程、權限、關聯採購單。"""
from app import create_app
from app.models import User, Project, ProcurementRequest, PaymentRequest, db

app = create_app()

with app.app_context():
    proj = Project.query.filter_by(code="PRJ-0002").first()
    if not proj:
        proj = Project(code="PRJ-TEST", name="t", status="active", owner_id=1, budget=1)
        db.session.add(proj); db.session.commit()
    proj_id = proj.id
    fin = User.query.filter_by(username="fin1").first()
    if not fin:
        fin = User(username="fin1", full_name="財務一號", role="finance")
        fin.set_password("fin123"); db.session.add(fin); db.session.commit()
    # 一筆已核准的採購單，供請款關聯
    pr = ProcurementRequest.query.filter_by(status="approved").first()
    if not pr:
        pr = ProcurementRequest(code="PRC-LINK", project_id=proj_id, requester_id=1,
                                item_name="link", qty=1, estimated_price=100,
                                status="approved")
        db.session.add(pr); db.session.commit()
    pr_id = pr.id

with app.test_client() as client:
    # 員工請款（關聯採購單）
    client.post("/login", data={"username": "emp1", "password": "emp123"})
    r = client.post("/payments/new", data={
        "payee": "供應商A", "invoice_no": "INV-1",
        "project_id": str(proj_id), "procurement_id": str(pr_id),
        "amount": "250", "currency": "TWD", "reason": "尾款"},
        follow_redirects=True)
    assert r.status_code == 200, f"new payment {r.status_code}"
    py = PaymentRequest.query.order_by(PaymentRequest.id.desc()).first()
    assert py.code.startswith("PAY-") and py.status == "submitted"
    assert py.procurement_id == pr_id, "採購單關聯失敗"
    print(f"[OK] 員工送出請款 {py.code}（關聯 {pr.code}）")

    # 員工無權核准
    r = client.post(f"/payments/{py.id}/approve", data={"decision": "approve"})
    assert r.status_code in (302, 403)
    assert PaymentRequest.query.get(py.id).status == "submitted"
    print("[OK] 員工無法核准請款（權限隔離正常）")

    # finance 核准 + 付款
    client.post("/login", data={"username": "fin1", "password": "fin123"})
    r = client.post(f"/payments/{py.id}/approve", data={"decision": "approve"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert PaymentRequest.query.get(py.id).status == "approved"
    print("[OK] finance 核准 -> approved")
    r = client.post(f"/payments/{py.id}/paid", follow_redirects=True)
    assert PaymentRequest.query.get(py.id).status == "paid"
    print("[OK] 標記已付款 -> paid")

print("\n=== 請款模組冒煙測試全部通過 ===")
