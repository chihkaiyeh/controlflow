from flask import Blueprint, render_template
from flask_login import current_user, login_required

from .models import InventoryItem, PaymentRequest, ProcurementRequest, Project
from .utils import date_str  # noqa: F401  (供未來儀表板用)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    stats = {
        "projects": Project.query.count(),
        "procurements": ProcurementRequest.query.count(),
        "payments": PaymentRequest.query.count(),
        "low_stock": InventoryItem.query.filter(
            InventoryItem.quantity <= InventoryItem.reorder_level
        ).count(),
    }
    recent_proc = (
        ProcurementRequest.query.order_by(ProcurementRequest.created_at.desc())
        .limit(5).all()
    )
    return render_template("main/dashboard.html", stats=stats,
                           recent_proc=recent_proc)
