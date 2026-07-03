"""User management business logic."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth import security
from app.crud.role import role as role_crud
from app.crud.user import user as user_crud
from app.models.user import User
from app.schemas.user import (
    PasswordUpdate,
    ProfileUpdate,
    UserCreate,
    UserUpdate,
)
from app.utils.exceptions import ConflictError, NotFoundError, ValidationError


def _ensure_unique(db: Session, username: str, email: str | None, exclude_id: int | None = None) -> None:
    existing = user_crud.get_by_username(db, username)
    if existing and existing.id != exclude_id:
        raise ConflictError(f"'{username}' username allaqachon band")
    if email:
        existing_email = user_crud.get_by_email(db, email)
        if existing_email and existing_email.id != exclude_id:
            raise ConflictError(f"'{email}' email allaqachon band")


def create_user(db: Session, data: UserCreate) -> User:
    """Create a new user with a hashed password."""
    _ensure_unique(db, data.username, data.email)
    if role_crud.get(db, data.role_id) is None:
        raise NotFoundError(f"Rol (id={data.role_id}) topilmadi")

    user = User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        role_id=data.role_id,
        is_active=data.is_active,
        hashed_password=security.hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    """Update an existing user (admin)."""
    payload = data.model_dump(exclude_unset=True)

    if "email" in payload and payload["email"]:
        existing_email = user_crud.get_by_email(db, payload["email"])
        if existing_email and existing_email.id != user.id:
            raise ConflictError(f"'{payload['email']}' email allaqachon band")

    if "role_id" in payload and payload["role_id"] is not None:
        if role_crud.get(db, payload["role_id"]) is None:
            raise NotFoundError(f"Rol (id={payload['role_id']}) topilmadi")

    for key, value in payload.items():
        setattr(user, key, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    """Update the current user's own profile."""
    payload = data.model_dump(exclude_unset=True)
    if "email" in payload and payload["email"]:
        existing_email = user_crud.get_by_email(db, payload["email"])
        if existing_email and existing_email.id != user.id:
            raise ConflictError(f"'{payload['email']}' email allaqachon band")
    for key, value in payload.items():
        setattr(user, key, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, data: PasswordUpdate) -> None:
    """Change the current user's password after verifying the old one."""
    if not security.verify_password(data.current_password, user.hashed_password):
        raise ValidationError("Joriy parol noto'g'ri")
    user.hashed_password = security.hash_password(data.new_password)
    db.add(user)
    db.commit()


def reset_password(db: Session, user: User, new_password: str) -> None:
    """Reset a user's password (admin action, no old-password check)."""
    user.hashed_password = security.hash_password(new_password)
    db.add(user)
    db.commit()


def set_active(db: Session, user: User, is_active: bool) -> User:
    """Activate or deactivate a user."""
    if user.is_superuser and not is_active:
        raise ValidationError("Administratorni nofaol qilib bo'lmaydi")
    user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
