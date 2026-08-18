from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from . import db
from .models import Project, ProcurementRequest, User
from .utils import next_code

proc_bp = Blueprint("procurements", __name__)


@proc_bp.route("/")
@login_required
def index():
    # 管理員/主管可看全部；一般員工只看自己
    if current_user.role in ("admin", "manager"):
        items = ProcurementRequest.query.order_by(
            ProcurementRequest.created_at.desc()).all()
    else:
        items = ProcurementRequest.query.filter_by(
            requester_id=current_user.id).order_by(
            ProcurementRequest.created_at.desc()).all()
    return render_template("procurements/list.html", items=items)


@proc_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    projects = Project.query.filter(Project.status != "closed").all()
    if request.method == "POST":
        item_name = request.form.get("item_name", "").strip()
        if not item_name:
            flash("品項名稱必填", "danger")
        else:
            pr = ProcurementRequest(
                code=next_code(ProcurementRequest, "PRC"),
                project_id=request.form.get("project_id") or None,
                requester_id=current_user.id,
                item_name=item_name,
                spec=request.form.get("spec", ""),
                qty=float(request.form.get("qty") or 1),
                unit=request.form.get("unit", ""),
                estimated_price=float(request.form.get("estimated_price") or 0),
                reason=request.form.get("reason", ""),
                status="submitted",
            )
            db.session.add(pr)
            db.session.commit()
            flash(f"已送出採購申請 {pr.code}", "success")
            return redirect(url_for("procurements.index"))
    return render_template("procurements/new.html", projects=projects)


@proc_bp.route("/<int:pid>/approve", methods=["POST"])
@login_required
def approve(pid):
    if current_user.role not in ("admin", "manager"):
        flash("無權核准", "danger")
        return redirect(url_for("procurements.index"))
    pr = ProcurementRequest.query.get_or_404(pid)
    decision = request.form.get("decision")
    if decision == "reject":
        pr.status = "rejected"
        flash(f"{pr.code} 已駁回", "warning")
    else:
        pr.status = "approved"
        pr.approver_id = current_user.id
        flash(f"{pr.code} 已核准", "success")
    db.session.commit()
    return redirect(url_for("procurements.index"))


@proc_bp.route("/<int:pid>/ordered", methods=["POST"])
@login_required
def ordered(pid):
    if current_user.role not in ("admin", "manager"):
        flash("無權操作", "danger")
        return redirect(url_for("procurements.index"))
    pr = ProcurementRequest.query.get_or_404(pid)
    pr.status = "ordered"
    db.session.commit()
    flash(f"{pr.code} 標記為已下單", "info")
    return redirect(url_for("procurements.index"))
