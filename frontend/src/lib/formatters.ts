/** Presentation formatters — pure functions for turning raw values into human-readable strings. */
const DEFAULT_LOCALE = "uz-UZ";

export function formatNumber(
  value: number | string | null | undefined,
  options: Intl.NumberFormatOptions = {}
): string {
  if (value == null) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat(DEFAULT_LOCALE, options).format(num);
}

/**
 * The one money formatter for the whole app: Uzbek so'm, thousands
 * separated with a plain space, no decimals, "so'm" suffix — e.g.
 * 1800 -> "1 800 so'm", 5780195.4 -> "5 780 195 so'm". Never shows a
 * currency symbol or code ($, USD, UZS).
 *
 * Grouping is done manually rather than via Intl.NumberFormat's uz-UZ
 * locale data: ICU's grouping separator for uz-UZ isn't guaranteed to be a
 * plain U+0020 space across engines/versions (the same class of ICU gap
 * documented on formatDate below, where uz-UZ month names silently fall
 * back to a raw token) — so this avoids depending on it for an exact,
 * byte-for-byte required format.
 */
export function formatMoney(value: number | string | null | undefined): string {
  if (value == null) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  const rounded = Math.round(num);
  const negative = rounded < 0;
  const digits = String(Math.abs(rounded));
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${negative ? "-" : ""}${grouped} so'm`;
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

/** The current moment, formatted for a `<input type="datetime-local">` default value (browser-local time, not UTC — `toISOString()` alone would shift it). */
export function nowForDatetimeLocalInput(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

/**
 * Display label for a unit of measure — capitalizes the seeded lowercase
 * short_name ("kg" -> "Kg", "qop" -> "Qop") without hardcoding any specific
 * unit. Falls back to "—" when the unit is missing or has a blank
 * short_name, matching the app's other missing-data placeholders.
 */
export function formatUnitLabel(unit: { short_name: string } | null | undefined): string {
  const raw = unit?.short_name?.trim();
  if (!raw) return "—";
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

/**
 * Quantity + unit as one string, e.g. "180 Qop". Render with
 * `whitespace-nowrap` (as other tabular-nums cells already do) so it never
 * splits across a line inside a narrow table cell.
 */
export function formatQuantity(
  quantity: number | string | null | undefined,
  unit: { short_name: string } | null | undefined
): string {
  if (quantity == null) return "—";
  const num = Number(quantity);
  if (Number.isNaN(num)) return "—";
  return `${formatNumber(quantity)} ${formatUnitLabel(unit)}`;
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
