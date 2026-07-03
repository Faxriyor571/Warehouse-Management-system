"""Stock-out (Chiqim / Sale) business logic.

Creating a sale atomically:
- validates products and available stock,
- computes line and document totals with discounts,
- decreases on-hand quantities,
- records payments (mixed payments supported),
- creates a debt for any unpaid remainder (requires a customer),
- records an audit entry.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.customer import customer as customer_crud
from app.crud.payment_method import payment_method as pm_crud
from app.crud.product import product as product_crud
from app.models.debt import Debt
from app.models.enums import AuditAction, DebtStatus, PaymentMethodType, PaymentStatus
from app.models.payment import Payment
from app.models.stock_out import StockOut, StockOutItem
from app.schemas.stock_out import StockOutCreate
from app.services import audit_service
from app.utils.exceptions import (
    InsufficientStockError,
    NotFoundError,
    ValidationError,
)
from app.utils.reference import generate_reference

_CENT = Decimal("0.01")


def _next_reference(db: Session) -> str:
    count = db.execute(select(func.count(StockOut.id))).scalar_one()
    return generate_reference("OUT", count + 1)


def create_stock_out(
    db: Session,
    data: StockOutCreate,
    *,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> StockOut:
    """Create a sale, decrease inventory and handle payments/debt."""
    if data.customer_id is not None and customer_crud.get(db, data.customer_id) is None:
        raise NotFoundError(f"Mijoz (id={data.customer_id}) topilmadi")

    # --- Phase 1: validate everything and compute totals (no mutation yet) ---
    computed: list[tuple[object, Decimal, Decimal, Decimal]] = []  # (product, qty, price, subtotal)
    subtotal_sum = Decimal("0")
    for line in data.items:
        product = product_crud.get(db, line.product_id)
        if product is None:
            raise NotFoundError(f"Mahsulot (id={line.product_id}) topilmadi")
        if not product.is_active:
            raise ValidationError(f"'{product.name}' mahsuloti faol emas")

        price = line.price if line.price is not None else product.sale_price
        line_gross = (line.quantity * price).quantize(_CENT)
        line_subtotal = (line_gross - line.discount).quantize(_CENT)
        if line_subtotal < 0:
            raise ValidationError(
                f"'{product.name}' uchun chegirma summadan katta bo'lishi mumkin emas"
            )
        if product.quantity < line.quantity:
            raise InsufficientStockError(
                f"'{product.name}' omborda yetarli emas "
                f"(mavjud: {product.quantity}, so'ralgan: {line.quantity})"
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

    # --- Phase 2: apply mutations ---
    header = StockOut(
        reference=_next_reference(db),
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
                customer_id=data.customer_id,  # validated non-None above
                stock_out_id=header.id,
                created_by_id=user_id,
                amount=remaining,
                paid_amount=Decimal("0"),
                remaining_amount=remaining,
                due_date=data.due_date,
                status=_debt_status(data.due_date),
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


def _status_for(paid: Decimal, total: Decimal) -> PaymentStatus:
    if paid <= 0:
        return PaymentStatus.UNPAID
    if paid >= total:
        return PaymentStatus.PAID
    return PaymentStatus.PARTIAL


def _debt_status(due: date | None) -> DebtStatus:
    from datetime import datetime, timezone

    if due is not None and due < datetime.now(timezone.utc).date():
        return DebtStatus.OVERDUE
    return DebtStatus.ACTIVE
