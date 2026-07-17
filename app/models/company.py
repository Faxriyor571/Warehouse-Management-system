"""Company (tenant) model.

A Company is a tenant of the platform (DATABASE_DESIGN.md §3.1). Companies
are never physically deleted — lifecycle is managed via ``status``.
"""
from __future__ import annotations

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import CompanyStatus
from app.models.mixins import TimestampMixin


class Company(Base, TimestampMixin):
    """A tenant business subscribing to the platform."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    status: Mapped[CompanyStatus] = mapped_column(
        SAEnum(CompanyStatus, name="company_status"),
        default=CompanyStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Company {self.slug}>"
