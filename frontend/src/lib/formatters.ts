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
