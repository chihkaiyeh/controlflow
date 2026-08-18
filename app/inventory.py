from flask import (Blueprint, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from . import db
from .models import InventoryItem, StockMovement
from .utils import next_code

inv_bp = Blueprint("inventory", __name__)


@inv_bp.route("/")
@login_required
def index():
    items = InventoryItem.query.order_by(InventoryItem.name).all()
    return render_template("inventory/list.html", items=items)


@inv_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if current_user.role not in ("admin", "warehouse"):
        flash("無權管理庫存", "danger")
        return redirect(url_for("inventory.index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("品名必填", "danger")
        else:
            item = InventoryItem(
                code=next_code(InventoryItem, "INV"),
                name=name,
                category=request.form.get("category", ""),
                unit=request.form.get("unit", ""),
                unit_price=float(request.form.get("unit_price") or 0),
                quantity=float(request.form.get("quantity") or 0),
                reorder_level=float(request.form.get("reorder_level") or 0),
                location=request.form.get("location", ""),
            )
            db.session.add(item)
            db.session.commit()
            flash(f"已建立品項 {item.code}", "success")
            return redirect(url_for("inventory.index"))
    return render_template("inventory/new.html")


@inv_bp.route("/<int:iid>/move", methods=["POST"])
@login_required
def move(iid):
    if current_user.role not in ("admin", "warehouse"):
        flash("無權調整庫存", "danger")
        return redirect(url_for("inventory.index"))
    item = InventoryItem.query.get_or_404(iid)
    direction = request.form.get("direction")
    try:
        qty = float(request.form.get("qty") or 0)
    except ValueError:
        qty = 0
    if qty <= 0:
        flash("數量必須大於 0", "danger")
        return redirect(url_for("inventory.index"))
    if direction == "out" and qty > item.quantity:
        flash("出庫數量大於現有庫存", "danger")
        return redirect(url_for("inventory.index"))
    item.quantity += qty if direction == "in" else -qty
    mv = StockMovement(item_id=item.id, type=direction, qty=qty,
                       note=request.form.get("note", ""),
                       user_id=current_user.id)
    db.session.add(mv)
    db.session.commit()
    verb = "入庫" if direction == "in" else "出庫"
    flash(f"{item.name} {verb} {qty} {item.unit or ''}", "info")
    return redirect(url_for("inventory.index"))


@inv_bp.route("/low")
@login_required
def low():
    items = InventoryItem.query.filter(
        InventoryItem.quantity <= InventoryItem.reorder_level).all()
    return render_template("inventory/list.html", items=items,
                           low_only=True)
