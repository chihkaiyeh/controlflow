from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from . import db
from .models import User

users_bp = Blueprint("users", __name__)

ROLES = ["admin", "manager", "finance", "warehouse", "employee"]
ROLE_LABEL = {
    "admin": "管理員", "manager": "主管", "finance": "財務",
    "warehouse": "倉管", "employee": "員工",
}


@users_bp.route("/")
@login_required
def index():
    if current_user.role != "admin":
        flash("僅管理員可管理成員", "danger")
        return redirect(url_for("main.dashboard"))
    users = User.query.order_by(User.id).all()
    return render_template("users/list.html", users=users,
                           ROLE_LABEL=ROLE_LABEL)


@users_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if current_user.role != "admin":
        flash("僅管理員可新增成員", "danger")
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "employee")
        if not username or not password:
            flash("帳號與密碼必填", "danger")
        elif User.query.filter_by(username=username).first():
            flash("帳號已存在", "danger")
        else:
            u = User(username=username, full_name=full_name, role=role)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            flash(f"已新增成員 {username}", "success")
            return redirect(url_for("users.index"))
    return render_template("users/new.html", ROLES=ROLES, ROLE_LABEL=ROLE_LABEL)


@users_bp.route("/<int:uid>/role", methods=["POST"])
@login_required
def set_role(uid):
    if current_user.role != "admin":
        flash("僅管理員可調整權限", "danger")
        return redirect(url_for("users.index"))
    u = User.query.get_or_404(uid)
    if u.id == current_user.id:
        flash("不能變更自己的角色", "warning")
        return redirect(url_for("users.index"))
    role = request.form.get("role")
    if role in ROLES:
        u.role = role
        db.session.commit()
        flash(f"{u.username} 角色已改為 {ROLE_LABEL.get(role, role)}", "success")
    return redirect(url_for("users.index"))


@users_bp.route("/<int:uid>/toggle", methods=["POST"])
@login_required
def toggle(uid):
    if current_user.role != "admin":
        flash("僅管理員可啟用/停用帳號", "danger")
        return redirect(url_for("users.index"))
    u = User.query.get_or_404(uid)
    if u.id == current_user.id:
        flash("不能停用自己", "warning")
        return redirect(url_for("users.index"))
    u.active = not u.active
    db.session.commit()
    flash(f"{u.username} 已{'啟用' if u.active else '停用'}", "info")
    return redirect(url_for("users.index"))


@users_bp.route("/<int:uid>/reset", methods=["POST"])
@login_required
def reset_pw(uid):
    if current_user.role != "admin":
        flash("僅管理員可重設密碼", "danger")
        return redirect(url_for("users.index"))
    u = User.query.get_or_404(uid)
    if u.id == current_user.id:
        flash("請用個人設定修改自己的密碼", "warning")
        return redirect(url_for("users.index"))
    pw = request.form.get("password", "").strip()
    if not pw:
        flash("密碼不可為空", "danger")
        return redirect(url_for("users.index"))
    u.set_password(pw)
    db.session.commit()
    flash(f"{u.username} 密碼已重設", "success")
    return redirect(url_for("users.index"))
