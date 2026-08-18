import os

from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for, send_from_directory, current_app)
from flask_login import current_user, login_required

from werkzeug.utils import secure_filename

from . import db
from .models import (Project, ProcurementRequest, PaymentRequest, User,
                     ProjectAttachment)
from .utils import next_code, parse_date, allowed_file, secure_name, human_size

projects_bp = Blueprint("projects", __name__)

PRIORITY_LABEL = {"high": "高", "medium": "中", "low": "低"}

ROLE_LABEL = {
    "admin": "管理員", "manager": "主管", "finance": "財務",
    "warehouse": "倉管", "employee": "員工",
}


@projects_bp.route("/")
@login_required
def index():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("projects/list.html", projects=projects,
                           PRIORITY_LABEL=PRIORITY_LABEL)


@projects_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    users = User.query.filter_by(active=True).all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("專案名稱必填", "danger")
        else:
            p = Project(
                code=next_code(Project, "PRJ"),
                name=name,
                description=request.form.get("description", ""),
                status=request.form.get("status", "planning"),
                priority=request.form.get("priority", "medium"),
                start_date=parse_date(request.form.get("start_date")),
                due_date=parse_date(request.form.get("due_date")),
                risk_assessment=request.form.get("risk_assessment", ""),
                stakeholders=request.form.get("stakeholders", ""),
                target_quality=request.form.get("target_quality", ""),
                owner_id=current_user.id,
                budget=float(request.form.get("budget") or 0),
            )
            db.session.add(p)
            db.session.commit()
            flash(f"已建立專案 {p.code}", "success")
            return redirect(url_for("projects.index"))
    return render_template("projects/new.html", users=users,
                           PRIORITY_LABEL=PRIORITY_LABEL)


@projects_bp.route("/<int:pid>")
@login_required
def detail(pid):
    p = Project.query.get_or_404(pid)
    procs = ProcurementRequest.query.filter_by(project_id=p.id).all()
    pays = PaymentRequest.query.filter_by(project_id=p.id).all()
    proc_total = sum(pr.estimated_price or 0 for pr in procs)
    pay_total = sum(py.amount or 0 for py in pays)
    members = [u for u in User.query.all()
               if u.full_name and u.full_name in (p.stakeholders or "")]
    return render_template("projects/detail.html", p=p, procs=procs, pays=pays,
                           proc_total=proc_total, pay_total=pay_total,
                           PRIORITY_LABEL=PRIORITY_LABEL,
                           ROLE_LABEL=ROLE_LABEL, members=members,
                           human_size=human_size)


@projects_bp.route("/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def edit(pid):
    p = Project.query.get_or_404(pid)
    users = User.query.filter_by(active=True).all()
    if request.method == "POST":
        p.name = request.form.get("name", "").strip() or p.name
        p.description = request.form.get("description", "")
        p.status = request.form.get("status", p.status)
        p.priority = request.form.get("priority", p.priority)
        p.start_date = parse_date(request.form.get("start_date"))
        p.due_date = parse_date(request.form.get("due_date"))
        p.risk_assessment = request.form.get("risk_assessment", "")
        p.stakeholders = request.form.get("stakeholders", "")
        p.target_quality = request.form.get("target_quality", "")
        p.budget = float(request.form.get("budget") or 0)
        db.session.commit()
        flash(f"{p.code} 已更新", "success")
        return redirect(url_for("projects.detail", pid=pid))
    return render_template("projects/edit.html", p=p, users=users,
                           PRIORITY_LABEL=PRIORITY_LABEL)


@projects_bp.route("/<int:pid>/close", methods=["POST"])
@login_required
def close(pid):
    p = Project.query.get_or_404(pid)
    p.status = "closed"
    db.session.commit()
    flash(f"專案 {p.code} 已結案", "info")
    return redirect(url_for("projects.detail", pid=pid))


# ---- 附件 ----
@projects_bp.route("/<int:pid>/upload", methods=["POST"])
@login_required
def upload(pid):
    p = Project.query.get_or_404(pid)
    f = request.files.get("file")
    if not f or f.filename == "":
        flash("未選擇檔案", "danger")
    elif not allowed_file(f.filename):
        flash("檔案類型不允許", "danger")
    else:
        folder = os.path.join(current_app.config["UPLOAD_FOLDER"], f"project_{pid}")
        os.makedirs(folder, exist_ok=True)
        safe = secure_name(f.filename)
        # 避免檔名重複：前綴時間戳
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        stored = f"{stamp}_{safe}"
        f.save(os.path.join(folder, stored))
        att = ProjectAttachment(
            project_id=pid, original_name=f.filename,
            stored_name=os.path.join(f"project_{pid}", stored),
            size=os.path.getsize(os.path.join(folder, stored)),
            uploader_id=current_user.id,
        )
        db.session.add(att)
        db.session.commit()
        flash("附件已上傳", "success")
    return redirect(url_for("projects.detail", pid=pid))


@projects_bp.route("/<int:pid>/attachment/<int:aid>")
@login_required
def attachment(pid, aid):
    att = ProjectAttachment.query.get_or_404(aid)
    if att.project_id != pid:
        abort(404)
    folder = current_app.config["UPLOAD_FOLDER"]
    directory = os.path.join(folder, f"project_{pid}")
    return send_from_directory(directory, os.path.basename(att.stored_name),
                               as_attachment=True,
                               download_name=att.original_name)


@projects_bp.route("/<int:pid>/attachment/<int:aid>/delete", methods=["POST"])
@login_required
def attachment_delete(pid, aid):
    att = ProjectAttachment.query.get_or_404(aid)
    if att.project_id != pid:
        abort(404)
    folder = current_app.config["UPLOAD_FOLDER"]
    path = os.path.join(folder, att.stored_name)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(att)
    db.session.commit()
    flash("附件已刪除", "info")
    return redirect(url_for("projects.detail", pid=pid))
