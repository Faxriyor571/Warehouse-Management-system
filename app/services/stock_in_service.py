"""Stock-in (Kirim) business logic.

Creating a stock-in document atomically, within one transaction owned by this
service (``apply_movement`` is called with ``commit=False``):

- validates the supplier (existence only — Suppliers is not company-scoped yet),
- validates each product within the caller's company,
- creates the header and line items,
- increases inventory:
    * tenant (CEO/Seller): per-store ``store_stock`` via ``inventory_service``,
      appending a ``stock_movements`` ledger row,
    * legacy admin (no company/store): the transitional ``product.quantity``
      path, kept until Sales is migrated,
- updates each product's latest purchase price,
- records an audit entry.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.product import product as product_crud
from app.crud.supplier import supplier as supplier_crud
from app.models.enums import AuditAction, MovementType
from app.models.stock_in import StockIn, StockInItem
from app.schemas.stock_in import StockInCreate
from app.services import audit_service, inventory_service
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.reference import generate_reference

_CENT = Decimal("0.01")


def _next_reference(db: Session, company_id: int | None) -> str:
    """Generate the next stock-in reference for a company.

    Isolated behind this helper so it can later be replaced by a proper
    sequence-based numbering service without touching the business logic below.
    (The current count-based scheme can collide under high concurrency — see the
    Phase 8 plan; a sequence table is the intended future replacement.)
    """
    stmt = select(func.count(StockIn.id))
    if company_id is None:
        stmt = stmt.where(StockIn.company_id.is_(None))
    else:
        stmt = stmt.where(StockIn.company_id == company_id)
    count = db.execute(stmt).scalar_one()
    return generate_reference("IN", count + 1)


def create_stock_in(
    db: Session,
    data: StockInCreate,
    *,
    company_id: int | None,
    store_id: int | None,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> StockIn:
    """Create an inbound delivery and increase inventory.

    ``company_id``/``store_id`` are resolved by the router from the caller
    (Seller → own store; CEO → validated body store; legacy admin → both None).
    """
    if data.supplier_id is not None and supplier_crud.get(db, data.supplier_id) is None:
        raise NotFoundError(f"Yetkazib beruvchi (id={data.supplier_id}) topilmadi")

    header = StockIn(
        reference=_next_reference(db, company_id),
        company_id=company_id,
        store_id=store_id,
        supplier_id=data.supplier_id,
        created_by_id=user_id,
        note=data.note,
        total_amount=Decimal("0"),
    )
    if data.date is not None:
        header.date = data.date
    db.add(header)
    db.flush()  # obtain header.id without committing

    # A store context (tenant) routes to the new store_stock ledger; its
    # absence (legacy admin) keeps the transitional product.quantity path.
    use_store_stock = company_id is not None and store_id is not None

    total = Decimal("0")
    for line in data.items:
        product = product_crud.get_for_company(db, line.product_id, company_id)
        if product is None:
            raise NotFoundError(f"Mahsulot (id={line.product_id}) topilmadi")
        if not product.is_active:
            raise ValidationError(f"'{product.name}' mahsuloti faol emas")

        subtotal = (line.quantity * line.price).quantize(_CENT)
        db.add(
            StockInItem(
                stock_in_id=header.id,
                product_id=product.id,
                quantity=line.quantity,
                price=line.price,
                subtotal=subtotal,
            )
        )

        if use_store_stock:
            inventory_service.apply_movement(
                db,
                company_id=company_id,  # type: ignore[arg-type]
                store_id=store_id,  # type: ignore[arg-type]
                product_id=product.id,
                movement_type=MovementType.STOCK_IN,
                quantity_delta=line.quantity,
                reference_type="stock_in",
                reference_id=header.id,
                created_by_id=user_id,
                commit=False,
            )
        else:  # TRANSITIONAL legacy path (removed when Sales is migrated)
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
