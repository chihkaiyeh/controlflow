from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from flask_login import UserMixin

from . import db


class User(UserMixin, db.Model):
    """系統使用者。role 決定可見/可操作的範圍。"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(256), nullable=False)
    # admin / manager(主管) / finance(財務) / warehouse(倉管) / employee(員工)
    role = db.Column(db.String(32), default="employee")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def __repr__(self):
        return f"<User {self.username}>"


class Project(db.Model):
    """專案：內控的主軸，採購與請款都掛在專案下。"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    # planning / active / closed
    status = db.Column(db.String(32), default="planning")
    # 優先層級：high / medium / low
    priority = db.Column(db.String(16), default="medium")
    # 時程
    start_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    # 執行風險評估、利害關係人、目標品質
    risk_assessment = db.Column(db.Text)
    stakeholders = db.Column(db.Text)
    target_quality = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    budget = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    owner = db.relationship("User", foreign_keys=[owner_id],
                            backref="owned_projects")


class ProjectAttachment(db.Model):
    """專案附件。"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    size = db.Column(db.Integer, default=0)
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    project = db.relationship("Project", backref="attachments")
    uploader = db.relationship("User", backref="uploaded_attachments")


class ProcurementRequest(db.Model):
    """採購申請：員工提出，主管核准後可下單。"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    item_name = db.Column(db.String(160), nullable=False)
    spec = db.Column(db.String(255))
    qty = db.Column(db.Float, default=1)
    unit = db.Column(db.String(16))
    estimated_price = db.Column(db.Float, default=0)
    reason = db.Column(db.Text)
    # submitted / approved / rejected / ordered
    status = db.Column(db.String(32), default="submitted")
    approver_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    project = db.relationship("Project", backref="procurements")
    requester = db.relationship("User", foreign_keys=[requester_id],
                                backref="procurement_requests")
    approver = db.relationship("User", foreign_keys=[approver_id],
                               backref="approved_procurements")


class PaymentRequest(db.Model):
    """請款：可對應採購單或一般費用，財務/主管核准後付款。"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    procurement_id = db.Column(db.Integer, db.ForeignKey("procurement_request.id"))
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    payee = db.Column(db.String(160))
    amount = db.Column(db.Float, default=0)
    currency = db.Column(db.String(8), default="TWD")
    invoice_no = db.Column(db.String(64))
    reason = db.Column(db.Text)
    # submitted / approved / rejected / paid
    status = db.Column(db.String(32), default="submitted")
    approver_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    project = db.relationship("Project", backref="payments")
    procurement = db.relationship("ProcurementRequest", backref="payments")
    requester = db.relationship("User", foreign_keys=[requester_id],
                                backref="payment_requests")
    approver = db.relationship("User", foreign_keys=[approver_id],
                               backref="approved_payments")


class InventoryItem(db.Model):
    """耗材庫存品項。"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(64))
    unit = db.Column(db.String(16))
    unit_price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Float, default=0)
    reorder_level = db.Column(db.Float, default=0)
    location = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class StockMovement(db.Model):
    """出入庫流水帳，用來追溯庫存變動。"""
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_item.id"))
    type = db.Column(db.String(8))  # in / out
    qty = db.Column(db.Float)
    note = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    item = db.relationship("InventoryItem", backref="movements")
    user = db.relationship("User", backref="stock_movements")
