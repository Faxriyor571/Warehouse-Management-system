"""Stock-in (Kirim) business logic.

Creating a stock-in document atomically:
- validates products,
- creates the header and line items,
- increases on-hand quantities,
- updates each product's latest purchase price,
- records an audit entry.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.product import product as product_crud
from app.crud.supplier import supplier as supplier_crud
from app.models.enums import AuditAction
from app.models.stock_in import StockIn, StockInItem
from app.schemas.stock_in import StockInCreate
from app.services import audit_service
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.reference import generate_reference


def _next_reference(db: Session) -> str:
    count = db.execute(select(func.count(StockIn.id))).scalar_one()
    return generate_reference("IN", count + 1)


def create_stock_in(
    db: Session,
    data: StockInCreate,
    *,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> StockIn:
    """Create an inbound delivery and increase inventory."""
    if data.supplier_id is not None and supplier_crud.get(db, data.supplier_id) is None:
        raise NotFoundError(f"Yetkazib beruvchi (id={data.supplier_id}) topilmadi")

    header = StockIn(
        reference=_next_reference(db),
        supplier_id=data.supplier_id,
        created_by_id=user_id,
        note=data.note,
        total_amount=Decimal("0"),
    )
    if data.date is not None:
        header.date = data.date
    db.add(header)
    db.flush()  # obtain header.id without committing

    total = Decimal("0")
    for line in data.items:
        product = product_crud.get(db, line.product_id)
        if product is None:
            raise NotFoundError(f"Mahsulot (id={line.product_id}) topilmadi")
        if not product.is_active:
            raise ValidationError(f"'{product.name}' mahsuloti faol emas")

        subtotal = (line.quantity * line.price).quantize(Decimal("0.01"))
        db.add(
            StockInItem(
                stock_in_id=header.id,
                product_id=product.id,
                quantity=line.quantity,
                price=line.price,
                subtotal=subtotal,
            )
        )
        # Increase inventory and remember latest purchase price.
        product.quantity = product.quantity + line.quantity
        product.purchase_price = line.price
        db.add(product)
        total += subtotal

    header.total_amount = total
    db.add(header)
    db.commit()
    db.refresh(header)

    audit_service.log_action(
        db,
        action=AuditAction.STOCK_IN,
        user_id=user_id,
        entity_type="stock_in",
        entity_id=header.id,
        description=f"Kirim {header.reference}: {len(data.items)} mahsulot, jami {total}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return header
