"""共用工具函式。"""
from datetime import datetime
from flask import current_app

from werkzeug.utils import secure_filename

from . import db
from .models import Project, ProcurementRequest, PaymentRequest, InventoryItem


def next_code(model, prefix, field="code"):
    """產生下一個序號代碼，例如 PRJ-0001、PRC-0007。

    model: SQLAlchemy 模型；prefix: 前綴；field: 代碼欄位名。
    邏輯：取該表代碼中前綴相符者，解析尾數最大值 +1。
    """
    col = getattr(model, field)
    rows = db.session.query(col).filter(col.like(f"{prefix}-%")).all()
    max_n = 0
    for (val,) in rows:
        try:
            n = int(val.split("-")[-1])
            max_n = max(max_n, n)
        except (ValueError, AttributeError):
            continue
    return f"{prefix}-{max_n + 1:04d}"


def date_str(dt):
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def parse_date(value):
    """把 'YYYY-MM-DD' 字串解析成 date，失敗/空白回 None。"""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", set())
    return ext in allowed


def human_size(n):
    """把 byte 數轉成可讀字串。"""
    n = n or 0
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def secure_name(filename):
    return secure_filename(filename)

