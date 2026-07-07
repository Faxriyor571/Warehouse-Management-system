"""Sales (Chiqim / Stock-out) business logic (API_SPECIFICATION.md §9).

Creating a sale atomically, within one transaction owned by this service
(``apply_movement`` is called with ``commit=False``):
- validates the customer (existence only — Customers is not company-scoped yet)
  and enforces legal-entity pricing (SRS rule #18),
- validates products and available stock,
- computes line and document totals with discounts,
- decreases inventory:
    * tenant (CEO/Seller): per-store ``store_stock`` via ``inventory_service``,
      appending a ``stock_movements`` ledger row,
    * legacy admin (no company/store): the transitional ``product.quantity``
      path, kept until Dashboard/Reports are migrated,
- records payments (mixed payments supported),
- creates a debt for any unpaid remainder (requires a customer),
- records an audit entry.

Sale Returns (``create_sales_return``) restore inventory at the original sale
price and reduce any linked debt, without ever modifying the original sale.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.customer import customer as customer_crud
from app.crud.payment_method import payment_method as pm_crud
from app.crud.product import product as product_crud
from app.crud.sales_return import sales_return as sales_return_crud
from app.crud.store_stock import store_stock as store_stock_crud
from app.models.debt import Debt
from app.models.enums import (
    AuditAction,
    CustomerType,
    MovementType,
    PaymentMethodType,
    PaymentStatus,
)
from app.models.payment import Payment
from app.models.sales_return import SalesReturn, SalesReturnItem
from app.models.stock_out import StockOut, StockOutItem
from app.schemas.sales_return import SalesReturnCreate
from app.schemas.stock_out import StockOutCreate
from app.services import audit_service, debt_service, inventory_service
from app.utils.exceptions import (
    InsufficientStockError,
    NotFoundError,
    ValidationError,
)
from app.utils.reference import generate_reference

_CENT = Decimal("0.01")


def _next_reference(db: Session, store_id: int | None) -> str:
    """Generate the next sale reference for a store.

    Isolated behind this helper so it can later be replaced by a proper
    sequence-based numbering service without touching the business logic
    below. Scoped by ``store_id`` (not company) per DATABASE_DESIGN.md §6 —
    sale references are unique within their store.
    """
    stmt = select(func.count(StockOut.id))
    if store_id is None:
        stmt = stmt.where(StockOut.store_id.is_(None))
    else:
        stmt = stmt.where(StockOut.store_id == store_id)
    count = db.execute(stmt).scalar_one()
    return generate_reference("OUT", count + 1)


def _next_return_reference(db: Session, store_id: int | None) -> str:
    """Generate the next sale-return reference for a store (same scheme)."""
    stmt = select(func.count(SalesReturn.id))
    if store_id is None:
        stmt = stmt.where(SalesReturn.store_id.is_(None))
    else:
        stmt = stmt.where(SalesReturn.store_id == store_id)
    count = db.execute(stmt).scalar_one()
    return generate_reference("RET", count + 1)


def create_stock_out(
    db: Session,
    data: StockOutCreate,
    *,
    company_id: int | None,
    store_id: int | None,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> StockOut:
    """Create a sale, decrease inventory and handle payments/debt."""
    customer = None
    if data.customer_id is not None:
        customer = customer_crud.get(db, data.customer_id)
        if customer is None:
            raise NotFoundError(f"Mijoz (id={data.customer_id}) topilmadi")

    use_store_stock = company_id is not None and store_id is not None

    # --- Phase 1: validate everything and compute totals (no mutation yet) ---
    computed: list[tuple[object, Decimal, Decimal, Decimal]] = []  # (product, qty, price, subtotal)
    subtotal_sum = Decimal("0")
    for line in data.items:
        product = product_crud.get_for_company(db, line.product_id, company_id)
        if product is None:
            raise NotFoundError(f"Mahsulot (id={line.product_id}) topilmadi")
        if not product.is_active:
            raise ValidationError(f"'{product.name}' mahsuloti faol emas")

        # Legal-entity pricing (SRS rule #18): a price override is accepted
        # only for a Legal Entity customer; otherwise the product's current
        # sale_price is authoritative.
        if line.price is not None and line.price != product.sale_price:
            if customer is None or customer.customer_type != CustomerType.LEGAL_ENTITY:
                raise ValidationError(
                    f"'{product.name}' uchun narxni faqat yuridik shaxs mijozlar uchun o'zgartirish mumkin"
                )
            price = line.price
        else:
            price = product.sale_price

        line_gross = (line.quantity * price).quantize(_CENT)
        line_subtotal = (line_gross - line.discount).quantize(_CENT)
        if line_subtotal < 0:
            raise ValidationError(
                f"'{product.name}' uchun chegirma summadan katta bo'lishi mumkin emas"
            )

        if use_store_stock:
            balance = store_stock_crud.get(db, store_id, product.id)  # type: ignore[arg-type]
            available = balance.quantity if balance is not None else Decimal("0")
        else:
            available = product.quantity
        if available < line.quantity:
            raise InsufficientStockError(
                f"'{product.name}' omborda yetarli emas "
                f"(mavjud: {available}, so'ralgan: {line.quantity})"
            )

        computed.append((product, line.quantity, price, line_subtotal))
        subtotal_sum += line_subtotal

    total_amount = (subtotal_sum - data.discount).quantize(_CENT)
    if total_amount < 0:
        raise ValidationError("Umumiy chegirma jami summadan katta bo'lishi mumkin emas")

    # --- Validate payments (only non-debt methods count as paid money) ---
    paid_amount = Decimal("0")
    valid_payments: list[tuple[int, Decimal, str | None]] = []
    for pay in data.payments:
        method = pm_crud.get(db, pay.payment_method_id)
        if method is None:
            raise NotFoundError(f"To'lov turi (id={pay.payment_method_id}) topilmadi")
        if method.type == PaymentMethodType.DEBT:
            # Debt-type "payment" is not real money; the remainder becomes a debt.
            continue
        paid_amount += pay.amount
        valid_payments.append((method.id, pay.amount, pay.note))

    paid_amount = paid_amount.quantize(_CENT)
    if paid_amount > total_amount:
        raise ValidationError("To'lov summasi jami summadan katta bo'lishi mumkin emas")

    remaining = (total_amount - paid_amount).quantize(_CENT)
    if remaining > 0 and data.customer_id is None:
        raise ValidationError("Qarz uchun mijoz tanlanishi shart")

    # --- Phase 2: apply mutations (single transaction, one commit) ---
    header = StockOut(
        reference=_next_reference(db, store_id),
        company_id=company_id,
        store_id=store_id,
        customer_id=data.customer_id,
        created_by_id=user_id,
        subtotal=subtotal_sum.quantize(_CENT),
        discount=data.discount,
        total_amount=total_amount,
        paid_amount=paid_amount,
        note=data.note,
        payment_status=_status_for(paid_amount, total_amount),
    )
    if data.date is not None:
        header.date = data.date
    db.add(header)
    db.flush()

    for product, qty, price, line_subtotal in computed:
        db.add(
            StockOutItem(
                stock_out_id=header.id,
                product_id=product.id,  # type: ignore[attr-defined]
                quantity=qty,
                price=price,
                discount=Decimal("0"),
                subtotal=line_subtotal,
            )
        )

        if use_store_stock:
            inventory_service.apply_movement(
                db,
                company_id=company_id,  # type: ignore[arg-type]
                store_id=store_id,  # type: ignore[arg-type]
                product_id=product.id,  # type: ignore[attr-defined]
                movement_type=MovementType.SALE,
                quantity_delta=-qty,
                reference_type="sale",
                reference_id=header.id,
                created_by_id=user_id,
                commit=False,
            )
        else:  # TRANSITIONAL legacy path (removed when Dashboard/Reports migrate)
            product.quantity = product.quantity - qty  # type: ignore[attr-defined]
            db.add(product)

    for method_id, amount, note in valid_payments:
        db.add(
            Payment(
                stock_out_id=header.id,
                payment_method_id=method_id,
                created_by_id=user_id,
                amount=amount,
                note=note,
            )
        )

    if remaining > 0:
        db.add(
            Debt(
                company_id=company_id,
                store_id=store_id,
                customer_id=data.customer_id,  # validated non-None above
                stock_out_id=header.id,
                created_by_id=user_id,
                amount=remaining,
                paid_amount=Decimal("0"),
                remaining_amount=remaining,
                due_date=data.due_date,
                status=debt_service._status_for_due(data.due_date, remaining=remaining),
                note=f"Savdodan qarz: {header.reference}",
            )
        )

    db.commit()
    db.refresh(header)

    audit_service.log_action(
        db,
        action=AuditAction.STOCK_OUT,
        user_id=user_id,
        entity_type="stock_out",
        entity_id=header.id,
        description=(
            f"Chiqim {header.reference}: jami {total_amount}, "
            f"to'landi {paid_amount}, qarz {remaining}"
        ),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return header


def create_sales_return(
    db: Session,
    sale: StockOut,
    data: SalesReturnCreate,
    *,
    company_id: int | None,
    store_id: int | None,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> SalesReturn:
    """Return part or all of a sale: restore inventory, reduce any linked debt.

    The original sale is never modified. Single transaction, one commit.
    """
    use_store_stock = company_id is not None and store_id is not None

    sale_items_by_id = {item.id: item for item in sale.items}

    computed: list[tuple[StockOutItem, Decimal, Decimal]] = []  # (original_item, qty, subtotal)
    total = Decimal("0")
    for line in data.items:
        original_item = sale_items_by_id.get(line.stock_out_item_id)
        if original_item is None:
            raise NotFoundError(
                f"Chiqim qatori (id={line.stock_out_item_id}) ushbu hujjatga tegishli emas"
            )

        already_returned = sales_return_crud.already_returned_quantity(db, original_item.id)
        remaining_returnable = original_item.quantity - already_returned
        if line.quantity > remaining_returnable:
            raise ValidationError(
                f"Qaytarish miqdori ruxsat etilgandan ko'p "
                f"(mavjud: {remaining_returnable}, so'ralgan: {line.quantity})"
            )

        subtotal = (line.quantity * original_item.price).quantize(_CENT)
        computed.append((original_item, line.quantity, subtotal))
        total += subtotal

    header = SalesReturn(
        reference=_next_return_reference(db, store_id),
        company_id=company_id,
        store_id=store_id,
        stock_out_id=sale.id,
        created_by_id=user_id,
        reason=data.reason,
        total_amount=total.quantize(_CENT),
    )
    db.add(header)
    db.flush()

    for original_item, qty, subtotal in computed:
        db.add(
            SalesReturnItem(
                sales_return_id=header.id,
                stock_out_item_id=original_item.id,
                product_id=original_item.product_id,
                quantity=qty,
                price=original_item.price,
                subtotal=subtotal,
            )
        )

        if use_store_stock:
            inventory_service.apply_movement(
                db,
                company_id=company_id,  # type: ignore[arg-type]
                store_id=store_id,  # type: ignore[arg-type]
                product_id=original_item.product_id,
                movement_type=MovementType.SALES_RETURN,
                quantity_delta=qty,
                reference_type="sales_return",
                reference_id=header.id,
                created_by_id=user_id,
                commit=False,
            )
        else:  # TRANSITIONAL legacy path (removed when Dashboard/Reports migrate)
            original_item.product.quantity = original_item.product.quantity + qty
            db.add(original_item.product)

    # Reduce any linked debt (floored at zero); the original sale document
    # itself is never modified (immutable — see module docstring).
    if sale.debt is not None and sale.debt.remaining_amount > 0:
        reduction = min(total, sale.debt.remaining_amount)
        sale.debt.remaining_amount = sale.debt.remaining_amount - reduction
        sale.debt.amount = sale.debt.amount - reduction
        sale.debt.status = debt_service._status_for_due(
            sale.debt.due_date, remaining=sale.debt.remaining_amount
        )
        db.add(sale.debt)

    db.commit()
    db.refresh(header)

    audit_service.log_action(
        db,
        action=AuditAction.SALES_RETURN,
        user_id=user_id,
        entity_type="sales_return",
        entity_id=header.id,
        description=f"Qaytarish {header.reference}: savdo {sale.reference}, jami {total}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return header


def _status_for(paid: Decimal, total: Decimal) -> PaymentStatus:
    if paid <= 0:
        return PaymentStatus.UNPAID
    if paid >= total:
        return PaymentStatus.PAID
    return PaymentStatus.PARTIAL
