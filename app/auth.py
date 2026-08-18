from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import (current_user, login_required, login_user,
                           logout_user)

from . import login_manager
from .models import User, db

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect(url_for("main.dashboard"))
        return render_template("auth/login.html")

    # POST：若已登入則先登出，允許切換帳號
    if current_user.is_authenticated:
        logout_user()

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password) and user.active:
        login_user(user)
        flash("登入成功", "success")
        return redirect(url_for("main.dashboard"))
    flash("帳號或密碼錯誤，或帳號已停用", "danger")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已登出", "info")
    return redirect(url_for("auth.login"))
