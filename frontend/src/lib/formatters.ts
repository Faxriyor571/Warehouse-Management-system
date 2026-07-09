/** Presentation formatters — pure functions for turning raw values into human-readable strings. */
const DEFAULT_LOCALE = "uz-UZ";
const DEFAULT_CURRENCY = "UZS";

export function formatNumber(
  value: number | string | null | undefined,
  options: Intl.NumberFormatOptions = {}
): string {
  if (value == null) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat(DEFAULT_LOCALE, options).format(num);
}

export function formatMoney(value: number | string | null | undefined): string {
  return formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Compact form for axis ticks / tight spaces — 300000 -> "300k", 5780120 -> "5.78m". */
export function formatCompactNumber(value: number | string | null | undefined): string {
  if (value == null) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat(DEFAULT_LOCALE, { notation: "compact", maximumFractionDigits: 1 }).format(num);
}

export function formatCurrency(
  value: number | string | null | undefined,
  currency: string = DEFAULT_CURRENCY
): string {
  if (value == null) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat(DEFAULT_LOCALE, { style: "currency", currency }).format(num);
}

/**
 * Numeric date fields, not `dateStyle`: Chromium's ICU data has no month-name
 * data for `uz-UZ`, so `dateStyle` silently falls back to a raw token like
 * "M07" instead of a month name. Numeric fields render correctly everywhere.
 */
export function formatDate(value: string | Date | null | undefined): string {
  if (value == null) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (value == null) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

/** Up-to-two-letter initials from a full name, for avatar fallbacks. */
export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return (parts[0]?.[0] ?? "?").toUpperCase();
  return `${parts[0]?.[0] ?? ""}${parts[parts.length - 1]?.[0] ?? ""}`.toUpperCase();
}

const BUSINESS_UTC_OFFSET_HOURS = 5;

/**
 * Today's calendar date (YYYY-MM-DD) in business-local (Uzbekistan, UTC+5)
 * time — mirrors the backend's `business_today()` so a "due today" debt
 * comparison agrees with the server regardless of the browser's own
 * timezone, the same way the backend avoids attributing late-night activity
 * to the wrong calendar day.
 */
export function businessTodayISO(): string {
  const shifted = Date.now() + BUSINESS_UTC_OFFSET_HOURS * 60 * 60 * 1000;
  return new Date(shifted).toISOString().slice(0, 10);
}
