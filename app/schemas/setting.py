"""Company setting schemas (API_SPECIFICATION.md §15)."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class SettingItem(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str | None = None


class SettingsUpdate(BaseModel):
    """PUT payload: a single ``{key, value}`` or a batch ``{settings: [...]}``."""

    key: str | None = Field(default=None, min_length=1, max_length=100)
    value: str | None = None
    settings: list[SettingItem] | None = None

    @model_validator(mode="after")
    def _exactly_one_form(self) -> "SettingsUpdate":
        has_single = self.key is not None
        has_batch = self.settings is not None
        if has_single == has_batch:
            raise ValueError("`key` yoki `settings` — bittasini yuboring (ikkalasini emas)")
        if has_batch and not self.settings:
            raise ValueError("`settings` bo'sh bo'lishi mumkin emas")
        return self

    def items(self) -> list[SettingItem]:
        """Normalise either form into a flat list of items."""
        if self.settings is not None:
            return self.settings
        return [SettingItem(key=self.key, value=self.value)]  # type: ignore[arg-type]
