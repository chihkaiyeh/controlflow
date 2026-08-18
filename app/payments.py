from flask import (Blueprint, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from . import db
from .models import Project, ProcurementRequest, PaymentRequest
from .utils import next_code

pay_bp = Blueprint("payments", __name__)


@pay_bp.route("/")
@login_required
def index():
    if current_user.role in ("admin", "manager", "finance"):
        items = PaymentRequest.query.order_by(
            PaymentRequest.created_at.desc()).all()
    else:
        items = PaymentRequest.query.filter_by(
            requester_id=current_user.id).order_by(
            PaymentRequest.created_at.desc()).all()
    return render_template("payments/list.html", items=items)


@pay_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    projects = Project.query.filter(Project.status != "closed").all()
    procs = ProcurementRequest.query.filter(
        ProcurementRequest.status.in_(["approved", "ordered"])).all()
    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        if amount <= 0:
            flash("請款金額必須大於 0", "danger")
        else:
            py = PaymentRequest(
                code=next_code(PaymentRequest, "PAY"),
                project_id=request.form.get("project_id") or None,
                procurement_id=request.form.get("procurement_id") or None,
                requester_id=current_user.id,
                payee=request.form.get("payee", ""),
                amount=amount,
                currency=request.form.get("currency", "TWD"),
                invoice_no=request.form.get("invoice_no", ""),
                reason=request.form.get("reason", ""),
                status="submitted",
            )
            db.session.add(py)
            db.session.commit()
            flash(f"已送出請款 {py.code}", "success")
            return redirect(url_for("payments.index"))
    return render_template("payments/new.html", projects=projects, procs=procs)


@pay_bp.route("/<int:pid>/approve", methods=["POST"])
@login_required
def approve(pid):
    if current_user.role not in ("admin", "manager", "finance"):
        flash("無權核准", "danger")
        return redirect(url_for("payments.index"))
    py = PaymentRequest.query.get_or_404(pid)
    if request.form.get("decision") == "reject":
        py.status = "rejected"
        flash(f"{py.code} 已駁回", "warning")
    else:
        py.status = "approved"
        py.approver_id = current_user.id
        flash(f"{py.code} 已核准", "success")
    db.session.commit()
    return redirect(url_for("payments.index"))


@pay_bp.route("/<int:pid>/paid", methods=["POST"])
@login_required
def paid(pid):
    if current_user.role not in ("admin", "manager", "finance"):
        flash("無權操作", "danger")
        return redirect(url_for("payments.index"))
    py = PaymentRequest.query.get_or_404(pid)
    py.status = "paid"
    db.session.commit()
    flash(f"{py.code} 標記為已付款", "info")
    return redirect(url_for("payments.index"))
