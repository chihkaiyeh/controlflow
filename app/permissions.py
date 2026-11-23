"""統一的角色授權 decorator。

使用時務必放在 @login_required 之內（下方），讓登入檢查先執行：

    @bp.route(...)
    @login_required
    @role_required("admin", "manager")
    def view(): ...
"""
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """限制可存取的角色，不符者回首頁並顯示訊息。"""
    roles = frozenset(roles)

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                flash("無權執行此操作", "danger")
                return redirect(url_for("main.dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator
