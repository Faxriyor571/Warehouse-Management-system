# API Specification — Warehouse ERP (Multi-Tenant)

**Document status:** Draft v1.0 — for review, not yet implemented
**Traces to:** [`WAREHOUSE_ERP_SPECIFICATION.md`](WAREHOUSE_ERP_SPECIFICATION.md) (SRS, authoritative) and
[`DATABASE_DESIGN.md`](DATABASE_DESIGN.md) (approved database design)

> This document is the **single source of truth** for every backend endpoint.
> It contains no backend code, no FastAPI code, no SQL, and no ORM models —
> those are implementation artifacts to be written after this specification is
> reviewed and approved.

Two conflicts were found while drafting this specification where the SRS and
the Database Design either did not fully cover a requested behavior, or
described it ambiguously. Rather than invent behavior, both are resolved with
the most conservative, already-approved-consistent reading and flagged
explicitly in [§16 Known Gaps & Follow-ups](#16-known-gaps--follow-ups). No
endpoint below assumes a table, column, or business rule that is not already
present in the approved documents, except where §16 explicitly says so.

---

## Table of Contents

0. [API Conventions](#0-api-conventions)
1. [Authentication](#1-authentication)
2. [Companies](#2-companies)
3. [Stores](#3-stores)
4. [Employees](#4-employees)
5. [Categories](#5-categories)
6. [Products](#6-products)
7. [Inventory](#7-inventory)
8. [Stock In](#8-stock-in)
9. [Sales](#9-sales)
10. [Customers](#10-customers)
11. [Debts](#11-debts)
12. [Expenses](#12-expenses)
13. [Dashboard](#13-dashboard)
14. [Reports](#14-reports)
15. [Settings](#15-settings)
16. [Known Gaps & Follow-ups](#16-known-gaps--follow-ups)

---

## 0. API Conventions

These conventions apply to every endpoint below and are not repeated per module.

- **Base path:** all endpoints are mounted under `/api/v1`.
- **Auth:** every endpoint except `POST /auth/login` and `POST /auth/refresh` requires
  `Authorization: Bearer <access_token>`.
- **Token claims:** the access token carries `sub` (user id), `role`
  (`super_admin` | `ceo` | `seller`), `company_id` (nullable), `store_id`
  (nullable), per [DATABASE_DESIGN.md §12](DATABASE_DESIGN.md#12-authentication-model).
  Every endpoint resolves tenancy/store scope **from these claims**, never
  from a client-supplied `company_id`/`store_id` in the request body or query
  string — a request can never assert a different company or store than the
  one on its own token.
- **Pagination:** list endpoints accept `page` (default `1`), `page_size`
  (default `20`, max `200`), and typically `search` (free-text). Response
  shape:
  ```
  { "items": [ ... ], "meta": { "page": 1, "page_size": 20, "total": 137, "total_pages": 7 } }
  ```
- **Errors:** a single convention across all endpoints:
  - `4xx` domain errors: `{ "detail": "<message>" }`
  - `422` validation errors: `{ "detail": "<message>", "errors": [ { "loc": [...], "msg": "..." } ] }`
  - `500` unhandled errors: `{ "detail": "<message>" }` (message generic in production)
- **Money / quantity:** money fields are decimal with 2 places; quantity
  fields are decimal with 3 places, matching
  [DATABASE_DESIGN.md](DATABASE_DESIGN.md).
- **Soft delete:** "delete" on a reference/master entity (categories, units,
  products, suppliers, customers) sets `deleted_at`; it never removes the row.
  Deleted records are excluded from list/detail endpoints and from selection
  in new documents, but remain intact on historical documents that reference
  them.
- **Access annotation:** every endpoint below states an **Access** line in the
  form `Access: <roles> — Seller: <own-store-only?> · CEO: <all-stores?> · Super Admin: <access?>`.

---

## 1. Authentication

**Purpose:** Authenticate a user and issue/refresh session tokens. Not a business
module — every other module depends on it.

**Roles allowed:** all (Super Admin, CEO, Seller) — this module has no role
restriction; it *establishes* the role.

### `POST /auth/login`

Access: Super Admin, CEO, Seller — Seller: n/a · CEO: n/a · Super Admin: n/a (unauthenticated endpoint)

- **Request body:**
  ```
  { "company_slug": "acme-agro" | null, "username": "string", "password": "string" }
  ```
  `company_slug` is required for CEO/Seller logins and omitted for Super Admin
  logins.
- **Response body:**
  ```
  { "access_token": "string", "refresh_token": "string", "token_type": "bearer",
    "user": { "id": 1, "role": "ceo", "company_id": 4, "store_id": null, "full_name": "..." } }
  ```
- **Validation rules:** `username`/`password` required; `company_slug` required
  unless the resolved user's `role = super_admin`.
- **Business rules:** login is resolved as `(company_slug, username)` for
  CEO/Seller since `users.username` is unique **only within a company**
  ([DATABASE_DESIGN.md §6](DATABASE_DESIGN.md#6-unique-constraints)); Super
  Admin usernames are globally unique among `company_id IS NULL` rows.
  `is_active = false` or `deleted_at IS NOT NULL` blocks login.
- **Error responses:** `401` invalid credentials; `403` account inactive;
  `404` unknown `company_slug`.
- **Permission rules:** none (public endpoint).
- **Notes:** a company suspended by Super Admin (`companies.status = 'suspended'`)
  blocks login for all of that company's CEO/Seller users with `403`.

### `POST /auth/refresh`

Access: Super Admin, CEO, Seller — Seller: n/a · CEO: n/a · Super Admin: n/a

- **Request:** `{ "refresh_token": "string" }`
- **Response:** new `{ "access_token", "refresh_token" }` pair (rotated).
- **Business rules:** the presented refresh token is checked against
  `refresh_tokens.token_hash`; expired or `revoked_at IS NOT NULL` tokens are
  rejected. On success the old token row is marked revoked and a new one is
  inserted (rotation).
- **Errors:** `401` invalid/expired/revoked token.

### `POST /auth/logout`

Access: Super Admin, CEO, Seller — Seller: own session · CEO: own session · Super Admin: own session

- **Request:** `{ "refresh_token": "string" }`
- **Response:** `204 No Content`
- **Business rules:** marks the given refresh token `revoked_at = now()`. Does
  not revoke other active sessions of the same user.

### `GET /auth/me`

Access: Super Admin, CEO, Seller — Seller: self · CEO: self · Super Admin: self

- **Response:** the caller's own user record (`id`, `role`, `company_id`,
  `store_id`, `full_name`, `email`, `phone`, `is_active`, `last_login_at`).
- **Notes:** used by the frontend to bootstrap the session and role-based UI.

---

## 2. Companies

**Purpose:** Onboard and manage the lifecycle of companies (tenants) on the
platform ([SRS §2.2](WAREHOUSE_ERP_SPECIFICATION.md), §4.11).

**Roles allowed:** Super Admin only. CEO and Seller have no access to this
module. Cross-company operational access (stores, employees, reports, etc.)
is granted separately, through the support-session mechanism at the bottom
of this section — see [SRS §2.2](WAREHOUSE_ERP_SPECIFICATION.md#22-system-owner-super-admin)
(amended 2026-07-09).

### `POST /companies`

Access: Super Admin only — Seller: no access · CEO: no access · Super Admin: full

- **Request:**
  ```
  { "name": "string", "slug": "string", "contact_email": "string|null",
    "contact_phone": "string|null",
    "ceo": { "username": "string", "full_name": "string", "password": "string", "email": "string|null" } }
  ```
- **Response:** the created `company` plus the created `ceo` user summary
  (password never echoed back).
- **Validation:** `slug` unique platform-wide
  ([DATABASE_DESIGN.md §6](DATABASE_DESIGN.md#6-unique-constraints)); `slug`
  URL-safe (lowercase, digits, hyphens); `ceo.username` required.
- **Business rules:** creates one `companies` row (`status = 'active'`) and
  exactly one `users` row with `role = 'ceo'`, `company_id` = the new
  company's id, `store_id = null`. A company always has exactly one CEO
  created at onboarding (SRS does not define multi-CEO support — see §16).
- **Errors:** `409` slug already exists; `422` invalid input.
- **Notes:** stores are created separately via [§3 Stores](#3-stores) after
  onboarding.

### `GET /companies`

Access: Super Admin only

- **Query:** `page`, `page_size`, `search` (name), `status` (`active`|`suspended`).
- **Response:** paginated list of companies (no business data, per SRS §3.1).

### `GET /companies/{id}`

Access: Super Admin only

- **Response:** company detail (name, slug, status, contact info, created_at).
  Does **not** include store list, product counts, or any financial data.

### `PUT /companies/{id}`

Access: Super Admin only

- **Request:** `{ "name": "string", "contact_email": "string|null", "contact_phone": "string|null" }`
- **Business rules:** `slug` is immutable after creation (used for login
  resolution and, potentially, external references) — not included in the
  update payload.

### `POST /companies/{id}/activate` / `POST /companies/{id}/suspend`

Access: Super Admin only

- **Response:** updated company with new `status`.
- **Business rules:** suspending a company blocks login for **all** of that
  company's users (CEO and every Seller) immediately; it does not delete or
  alter any data ([DATABASE_DESIGN.md §9](DATABASE_DESIGN.md#9-delete-rules) —
  companies are never physically deleted).
- **Notes:** recommend also revoking all active refresh tokens for the
  company's users on suspend, so already-issued access tokens expire naturally
  and refresh is blocked.

### `POST /companies/{id}/support-session`

Access: Super Admin only — Seller: no access · CEO: no access · Super Admin: full

*Added 2026-07-09 — the mechanism behind the System Owner's cross-company
access described in [SRS §2.2](WAREHOUSE_ERP_SPECIFICATION.md#22-system-owner-super-admin).*

- **Response:**
  ```
  { "access_token": "string", "token_type": "bearer",
    "company": { "id", "name", "slug", "status", "contact_email", "contact_phone", "created_at", "updated_at" } }
  ```
  Deliberately **access-token-only** — no `refresh_token`. A support session
  is short-lived by design (expires with the normal access-token TTL) and
  must be explicitly re-opened; it is never silently extended.
- **Business rules:** issues a token that resolves (server-side, per request)
  to a CEO-equivalent identity scoped to `company_id = {id}`, `store_id =
  null` — the same access shape as that company's own CEO, which already
  covers every store, employee, report, dashboard, setting, inventory
  record, sale, debt, and expense in the company. The token's subject
  remains the System Owner's real user id, so every action taken during the
  session is audit-logged under their real identity, not a fabricated one
  (`GET /audit-log`, entity/description reflect the real actor).
  `GET /auth/me` while a support session is active returns
  `is_support_session: true`, `support_company_id`, and
  `support_company_name` so the caller can render an "acting as" indicator.
- **Errors:** `404` unknown company; `422` company is not `active`
  (suspended companies cannot be entered); `403` caller is not a System
  Owner.
- **Notes:** there is no corresponding "exit" endpoint — the client simply
  discards the support-session access token and resumes its own System
  Owner session token, which it must have retained separately.

---

## 3. Stores

**Purpose:** Represent the physical stores operated by a company (SRS §4.3).

### `POST /stores`

Access: CEO only — Seller: no access · CEO: full (own company) · Super Admin: full, via support session (§2.2, amended) (SRS §3.1)

- **Request:** `{ "name": "string", "address": "string|null", "phone": "string|null" }`
- **Response:** created store (`company_id` from token, never client-supplied).
- **Business rules:** a company may operate one or many stores (SRS §4.3); no
  upper limit defined.

### `GET /stores`

Access: CEO, Seller — Seller: sees all company stores' **names only** (for
cross-store inventory browsing, §7) · CEO: full detail, all stores · Super Admin: full, via support session (§2.2, amended)

- **Response for CEO:** full store list including `is_active`.
- **Response for Seller:** reduced shape `{ "id", "name" }` only — no address,
  phone, or activity status — since a Seller's only legitimate need to see
  other stores is to resolve store names when browsing cross-store inventory
  quantities ([SRS rule #4](WAREHOUSE_ERP_SPECIFICATION.md)).

### `GET /stores/{id}`

Access: CEO (any store in own company), Seller (**own assigned store only**) — Super Admin: full, via support session (§2.2, amended)

- **Errors:** `403` if a Seller requests a store other than their own
  `store_id` claim.

### `PUT /stores/{id}` / `POST /stores/{id}/deactivate`

Access: CEO only

- **Request (PUT):** `{ "name": "string", "address": "string|null", "phone": "string|null" }`
- **Business rules:** deactivation (`is_active = false`) is the only removal
  path — a store with any recorded stock, sales, expenses, or debts is never
  hard-deleted ([DATABASE_DESIGN.md §9](DATABASE_DESIGN.md#9-delete-rules)).
- **Errors:** `409` if attempting to deactivate a store that still has an
  assigned Seller — reassign or deactivate the Seller first (see §4).

---

## 4. Employees

**Purpose:** Manage the company's Seller accounts and their store assignment
(SRS §4.9). This module manages **Sellers only** — the CEO account itself is
created once during company onboarding (§2) and is not managed here; the SRS
defines no multi-CEO capability.

### `POST /employees`

Access: CEO only — Seller: no access · CEO: full (own company) · Super Admin: full, via support session (§2.2, amended)

- **Request:**
  ```
  { "username": "string", "full_name": "string", "password": "string",
    "email": "string|null", "phone": "string|null", "store_id": 12 }
  ```
- **Response:** created Seller user (`role = "seller"`, `company_id` from
  token, `store_id` as given).
- **Validation:** `username` unique within the company
  ([DATABASE_DESIGN.md §6](DATABASE_DESIGN.md#6-unique-constraints));
  `store_id` required and must belong to the same company.
- **Business rules:** a Seller is always assigned to **exactly one** store
  ([DATABASE_DESIGN.md §12](DATABASE_DESIGN.md#12-authentication-model):
  `store_id IS NOT NULL ⟺ role = 'seller'`).
- **Errors:** `409` username taken; `404` `store_id` not found in company;
  `422` missing `store_id`.

### `GET /employees` / `GET /employees/{id}`

Access: CEO only

- **Response:** Seller list/detail with assigned store name, `is_active`,
  `last_login_at`.

### `PUT /employees/{id}`

Access: CEO only

- **Request:** `{ "full_name": "string", "email": "string|null", "phone": "string|null", "store_id": 12 }`
- **Business rules:** changing `store_id` reassigns the Seller to a different
  store **effective immediately** — in-flight/incomplete work is not a
  concept in this schema (no draft sales — see §9), so reassignment is safe at
  any time.

### `POST /employees/{id}/activate` / `POST /employees/{id}/deactivate`

Access: CEO only

- **Business rules:** deactivation blocks login; it does not affect any
  historical `sales`, `stock_in`, `expenses`, or `debts` rows the Seller
  created (`created_by_id` is preserved, RESTRICT delete rule).

### `POST /employees/{id}/reset-password`

Access: CEO only

- **Request:** `{ "new_password": "string" }`
- **Response:** `204 No Content`.
- **Notes:** recommend revoking the Seller's existing refresh tokens on
  reset, forcing re-login with the new password.

---

## 5. Categories

**Purpose:** Maintain the product category catalogue (referenced by
[§6 Products](#6-products)).

### `POST /categories` / `PUT /categories/{id}` / `DELETE /categories/{id}`

Access: CEO only — Seller: no write access · CEO: full (own company) · Super Admin: full, via support session (§2.2, amended)

- **Request:** `{ "name": "string" }`
- **Validation:** `name` unique within the company
  ([DATABASE_DESIGN.md §6](DATABASE_DESIGN.md#6-unique-constraints)).
- **Business rules:** `DELETE` sets `deleted_at`; existing products keep their
  `category_id` reference (RESTRICT — the category itself is never hard
  removed while referenced).
- **Errors:** `409` duplicate name.

### `GET /categories` / `GET /categories/{id}`

Access: CEO, Seller — Seller: read-only, own company · CEO: full, own company · Super Admin: full, via support session (§2.2, amended)

- **Response:** paginated list / single category, excluding soft-deleted rows.

---

## 6. Products

**Purpose:** Maintain the fertilizer product catalogue (SRS §4.2).

### `POST /products`

Access: CEO only — Seller: no write access · CEO: full (own company) · Super Admin: full, via support session (§2.2, amended)

- **Request:**
  ```
  { "name": "string", "sku": "string", "barcode": "string|null",
    "category_id": 3, "unit_id": 1,
    "purchase_price": "0.00", "sale_price": "0.00",
    "description": "string|null" }
  ```
- **Validation:** `sku` unique within the company; `barcode` unique within the
  company when present ([DATABASE_DESIGN.md §6](DATABASE_DESIGN.md#6-unique-constraints));
  `category_id`/`unit_id` must belong to the same company.
- **Business rules:** quantities follow the 1 bag = 50 kg convention via the
  product's `unit.conversion_factor` (SRS rule #8;
  [DATABASE_DESIGN.md §3.6](DATABASE_DESIGN.md#3-table--column-reference)).
  On-hand quantity is **not** part of this payload — it does not exist on
  `products` (removed from the design, [§11](DATABASE_DESIGN.md#11-store-inventory-model));
  a newly created product starts with zero stock everywhere until a
  [Stock In](#8-stock-in) is recorded.
- **Errors:** `409` duplicate `sku`/`barcode`; `404` invalid `category_id`/`unit_id`.

### `GET /products` / `GET /products/{id}`

Access: CEO, Seller — Seller: read-only, own company (quantity shown for own
store; see [§7 Inventory](#7-inventory) for cross-store) · CEO: full, own
company · Super Admin: full, via support session (§2.2, amended)

- **Query (list):** `page`, `page_size`, `search`, `category_id`.
- **Response:** product fields plus **the caller's own-store quantity**
  (joined from `store_stock` for the caller's `store_id`; for CEO, from the
  store given by an optional `store_id` query param, defaulting to a
  company-wide total across stores).
- **Notes:** `barcode` and `image` are accepted/returned as plain optional
  fields (already present in the approved schema), but this specification
  deliberately does **not** define a barcode-lookup endpoint or an image
  upload endpoint — both are explicit SRS Future Roadmap items (§8) not yet
  confirmed. See [§16](#16-known-gaps--follow-ups).

### `PUT /products/{id}` / `DELETE /products/{id}`

Access: CEO only

- **Business rules:** `DELETE` sets `deleted_at`; `sale_price`/`purchase_price`
  changes apply only to future documents — historical `stock_in_items` and
  `sale_items` keep the price recorded at the time of the transaction
  (immutable line-item pricing, per existing schema design).

---

## 7. Inventory

**Purpose:** Expose per-store on-hand stock and its movement history — the
direct implementation of
[DATABASE_DESIGN.md §11 Store Inventory Model](DATABASE_DESIGN.md#11-store-inventory-model).
This module is **read-only**: `store_stock` and `stock_movements` are only
ever mutated as a side effect of [Stock In](#8-stock-in),
[Sales](#9-sales), and Sale Returns — there is no direct write endpoint (see
[§16](#16-known-gaps--follow-ups) regarding manual adjustments).

### `GET /inventory/store-stock`

Access: CEO, Seller — Seller: **own store only** · CEO: any store in own
company (via `store_id` query param) or company-wide totals · Super Admin: full, via support session (§2.2, amended)

- **Query:** `store_id` (CEO only — required for Seller's own store
  implicitly), `page`, `page_size`, `search` (product name/SKU).
- **Response:** `{ "product_id", "product_name", "sku", "quantity" }[]` for
  the resolved store.
- **Business rules:** a Seller may never pass a `store_id` other than their
  own — enforced server-side regardless of query param (SRS rule #3).

### `GET /inventory/store-stock/cross-store`

Access: CEO, Seller — Seller: **quantity-only, all company stores** · CEO: same, though redundant with §7's CEO company-wide view · Super Admin: full, via support session (§2.2, amended)

- **Query:** `product_id` (required).
- **Response:** `{ "store_id", "store_name", "quantity" }[]` — one row per
  store in the company that has ever stocked the product.
- **Business rules:** this is the exact, narrow implementation of SRS rule
  #4 — it returns **quantity only**. It never joins `sales`, `debts`,
  `expenses`, `customers`, or `stock_in`
  ([DATABASE_DESIGN.md §11](DATABASE_DESIGN.md#11-store-inventory-model)). A
  Seller calling this endpoint sees every store's quantity for the given
  product, including stores other than their own — this is the one
  explicitly permitted cross-store view.
- **Errors:** `404` unknown `product_id` (or not belonging to caller's company).

### `GET /inventory/movements`

Access: CEO, Seller — Seller: own store only · CEO: any store / company-wide · Super Admin: full, via support session (§2.2, amended)

- **Query:** `store_id`, `product_id`, `movement_type`
  (`stock_in`|`sale`|`sales_return`), `date_from`, `date_to`, `page`, `page_size`.
- **Response:** paginated `stock_movements` rows (`movement_type`,
  `quantity_delta`, `reference_type`, `reference_id`, `created_at`,
  `created_by`).
- **Notes:** this is the audit/reconciliation ledger described in
  [DATABASE_DESIGN.md §11](DATABASE_DESIGN.md#11-store-inventory-model); it is
  informational only and has no create/update/delete operations.

---

## 8. Stock In

**Purpose:** Record incoming goods received at a store (SRS §4.5).

### `POST /stock-in`

Access: CEO, Seller — Seller: **own store only** (`store_id` implied from
token, not accepted in the request body) · CEO: any store in own company
(`store_id` required in body) · Super Admin: full, via support session (§2.2, amended)

- **Request:**
  ```
  { "store_id": 12, "supplier_id": 3 | null, "date": "2026-07-06T00:00:00Z" | null,
    "note": "string|null",
    "items": [ { "product_id": 5, "quantity": "10.000", "price": "12000.00" } ] }
  ```
  (`store_id` omitted entirely for Seller callers — resolved from the token.)
- **Response:** created `stock_in` document with computed `total_amount` and
  its `items`.
- **Validation:** `items` non-empty; each `product_id` must belong to the
  caller's company; `quantity` > 0; `price` >= 0.
- **Business rules:** **Stock In increases inventory** (SRS rule #9) — for
  each line, `store_stock.quantity` for `(store_id, product_id)` is
  increased by `quantity` (creating the `store_stock` row if it doesn't yet
  exist), and a `stock_movements` row (`movement_type = "stock_in"`, positive
  `quantity_delta`) is appended in the same transaction. The document's
  `total_amount` is the sum of line subtotals (`quantity * price`). Quantities
  follow the 1 bag = 50 kg convention (SRS rule #8).
- **Errors:** `404` unknown `product_id`/`supplier_id`; `422` empty `items`
  or non-positive `quantity`.
- **Notes:** stock-in documents are **immutable** once created — there is no
  `PUT`/`DELETE`. See [§16](#16-known-gaps--follow-ups) for correction
  workflow status.

### `GET /stock-in` / `GET /stock-in/{id}`

Access: CEO, Seller — Seller: own store only · CEO: any store / company-wide · Super Admin: full, via support session (§2.2, amended)

- **Query (list):** `store_id` (CEO only), `supplier_id`, `date_from`,
  `date_to`, `search` (reference), `page`, `page_size`.
- **Response:** document header + `items` (with product name/SKU joined).

---

## 9. Sales

**Purpose:** Record sales of products to customers, including credit sales
(SRS §4.6). This is the platform's highest-traffic, most business-rule-dense
module.

### `POST /sales`

Access: CEO, Seller — Seller: **own store only** (`store_id` implied from
token) · CEO: any store in own company (`store_id` required in body) · Super Admin: full, via support session (§2.2, amended)

- **Request:**
  ```
  { "store_id": 12, "customer_id": 7 | null, "discount": "0.00",
    "note": "string|null",
    "items": [ { "product_id": 5, "quantity": "2.000", "price": "15000.00" | null, "discount": "0.00" } ],
    "payments": [ { "payment_method_id": 2, "amount": "20000.00" } ],
    "due_date": "2026-08-01" | null }
  ```
- **Response:** created `sale` with computed `subtotal`, `total_amount`,
  `paid_amount`, `payment_status`, its `items`, its `payments`, and the
  created `debt` if any balance remains unpaid.
- **Validation:** `items` non-empty; `quantity` > 0; sum of `payments` must
  not exceed `total_amount`; `due_date` required if the sale will leave a
  remaining balance and a debt reminder is expected (see [§11 Debts](#11-debts)).
- **Business rules (SRS §4.6, rules #10, #18, #19; [DATABASE_DESIGN.md §3.14](DATABASE_DESIGN.md#3-table--column-reference)):**
  - **Sales decrease inventory** of the selling store — each line reduces
    `store_stock.quantity` for `(store_id, product_id)` and appends a
    `stock_movements` row (`movement_type = "sale"`, negative
    `quantity_delta`). Rejected with `409 InsufficientStock` if the store's
    on-hand quantity is less than the requested `quantity`.
  - **Price behavior / legal entity pricing (SRS rule #18):** if `items[].price`
    is omitted, the product's current `sale_price` is used. If `items[].price`
    is supplied and differs from `sale_price`, it is accepted **only** when
    the resolved `customer.customer_type` is Legal Entity
    (`legal_entity` — see [§16](#16-known-gaps--follow-ups) on the value's
    exact wire name); a price-override attempt against an Individual customer,
    or against no customer at all, is rejected with `422`.
  - **Cash / partial / full-debt payment behavior:** `payments` may fully
    cover `total_amount` (cash sale, `payment_status = "paid"`, no debt), may
    partially cover it (`payment_status = "partial"`, a `debt` is created for
    the remainder), or may be empty (`payment_status = "unpaid"`, the entire
    `total_amount` becomes a `debt`). Any remaining balance **requires**
    `customer_id` to be set — `422` if a balance remains and no customer is
    given (SRS rule #10, #7).
  - **Sale finalization / cancellation (SRS rule #19):** a sale row is created
    only once, atomically, in this single request — there is no draft/pending
    state persisted server-side. "Cancellation before finalization" is
    therefore a **client-side concept only**: abandoning the in-progress
    sale form before calling this endpoint. Once `POST /sales` succeeds, the
    resulting row can never be cancelled or deleted — the only reversal path
    is [Sale Return](#post-salesidreturns), per SRS rule #19. There is no
    `DELETE /sales/{id}` or `POST /sales/{id}/cancel` endpoint.
- **Errors:** `404` unknown `product_id`/`customer_id`/`payment_method_id`;
  `409` insufficient stock; `422` payments exceeding total, missing customer
  for a remaining balance, or an unauthorized price override.

### `GET /sales` / `GET /sales/{id}`

Access: CEO, Seller — Seller: own store only · CEO: any store / company-wide · Super Admin: full, via support session (§2.2, amended)

- **Query (list):** `store_id` (CEO only), `customer_id`, `payment_status`,
  `date_from`, `date_to`, `search` (reference), `page`, `page_size`.
- **Response:** document header + `items` + `payments` + linked `debt` (if any).

### `POST /sales/{id}/returns`

Access: CEO, Seller — Seller: own store only (must match the original sale's
store) · CEO: any store in own company · Super Admin: full, via support session (§2.2, amended)

- **Request:**
  ```
  { "reason": "string|null",
    "items": [ { "sale_item_id": 41, "quantity": "1.000" } ] }
  ```
- **Response:** created `sales_return` with computed `total_amount` and its
  `sales_return_items`.
- **Validation:** each `sale_item_id` must belong to `{id}`'s sale; returned
  `quantity` must not exceed that line's original `quantity` minus any
  quantity already returned on prior returns against the same line.
- **Business rules (SRS rule #11; [DATABASE_DESIGN.md §3.16–§3.17](DATABASE_DESIGN.md#3-table--column-reference)):**
  - **Returns restore inventory using the original sale price** — for each
    line, `store_stock.quantity` is increased by the returned `quantity`
    (`stock_movements`, `movement_type = "sales_return"`, positive
    `quantity_delta`); the return's line `price` is always copied from the
    original `sale_items.price`, never re-entered by the caller.
  - **Effect on debt:** if the original sale has a linked `debt` with
    `remaining_amount > 0`, the returned line's amount
    (`quantity * original price`) reduces `debt.remaining_amount` (and
    `debt.amount`), floored at zero. If the sale was fully paid (no debt, or
    the debt is already fully paid), the return only restores inventory —
    this specification does not define a cash-refund mechanism (no
    refund-type payment exists in the approved schema); see
    [§16](#16-known-gaps--follow-ups).
  - The original `sale` row is never modified — it remains an accurate,
    immutable historical record; the return is a separate, linked document.
- **Errors:** `404` unknown `sale_item_id`; `422` return quantity exceeds
  remaining returnable quantity; `403` store mismatch for a Seller.

### `GET /sales/{id}/returns`

Access: CEO, Seller — same scope as `GET /sales/{id}`

- **Response:** list of `sales_returns` linked to the sale.

---

## 10. Customers

**Purpose:** Maintain records of the farmers and businesses the company sells
to (SRS §4.4). Customers are **company-wide** records, not store-scoped —
[DATABASE_DESIGN.md §3.11](DATABASE_DESIGN.md#3-table--column-reference) gives
`customers` a `company_id` only, no `store_id` — so any Seller in the company
can find/manage any company customer; only that customer's **linked
financial history** (sales, debts) is store-filtered for a Seller.

### `POST /customers`

Access: CEO, Seller — Seller: create only, company-wide · CEO: full · Super Admin: full, via support session (§2.2, amended)

- **Request:**
  ```
  { "full_name": "string", "customer_type": "individual" | "legal_entity",
    "phone": "string|null", "address": "string|null", "passport": "string|null" }
  ```
- **Validation:** `full_name` required; `customer_type` required, one of the
  two enumerated values (SRS rule #17).
- **Business rules:** `customer_type` cannot be changed casually after
  creation if it would invalidate a pricing decision already made on a past
  sale — past sales keep their own recorded `price`, so retroactive
  consistency is not actually at risk; changing type is allowed via `PUT`.

### `GET /customers` / `GET /customers/{id}`

Access: CEO, Seller — Seller: company-wide customer list, **but debt/sales
history in the detail view is filtered to the Seller's own store** · CEO: full,
all stores' history · Super Admin: full, via support session (§2.2, amended)

- **Query (list):** `page`, `page_size`, `search` (name/phone), `customer_type`.
- **Response (detail):** customer fields plus a debt summary
  (`total_outstanding`, computed per [§11 Debts](#11-debts)) and recent sales
  — both scoped to the caller's store for a Seller, company-wide for a CEO.

### `PUT /customers/{id}`

Access: CEO, Seller — same scope as create

- **Request:** same shape as create (partial update).

### `POST /customers/{id}/deactivate`

Access: CEO only

- **Business rules:** soft delete (`deleted_at`); a customer with any
  outstanding debt cannot be deactivated (`409`) — settle or write off the
  debt first (write-off is not itself a defined operation in this
  specification; see [§16](#16-known-gaps--follow-ups)).

---

## 11. Debts

**Purpose:** Track outstanding customer debt, its repayment, and due-date
reminders (SRS §4.8, rules #7, #20, #21, #22).

### `GET /debts` / `GET /debts/{id}`

Access: CEO, Seller — Seller: own store only · CEO: any store / company-wide · Super Admin: full, via support session (§2.2, amended)

- **Query (list):** `store_id` (CEO only), `customer_id`, `status`
  (`active`|`paid`|`overdue`), `due_before`, `due_after`, `page`, `page_size`.
- **Response:** debt fields plus `remaining_amount`, `status`, and (detail)
  its `debt_payments` history.
- **Balance calculation:** `remaining_amount = amount - paid_amount`, kept in
  sync on every `debt_payments` insert and every linked
  [Sale Return](#post-salesidreturns) (SRS rule #7,
  [DATABASE_DESIGN.md §3.20](DATABASE_DESIGN.md#3-table--column-reference)).
  `status` transitions: `active → paid` when `remaining_amount` reaches 0;
  `active → overdue` when `due_date` has passed and `remaining_amount > 0`;
  `overdue → paid` on full settlement.

### `POST /debts/{id}/payments`

Access: CEO, Seller — Seller: own store only · CEO: any store in own company · Super Admin: full, via support session (§2.2, amended)

- **Request:** `{ "payment_method_id": 2, "amount": "5000.00", "note": "string|null" }`
- **Response:** updated `debt` (`paid_amount`, `remaining_amount`, `status`)
  plus the created `debt_payments` row.
- **Validation:** `amount` > 0 and not exceeding `remaining_amount`.
- **Business rules:** partial payments are fully supported — any number of
  payments may be recorded against a debt until `remaining_amount` reaches 0.
- **Errors:** `422` amount exceeds remaining balance; `404` unknown
  `payment_method_id`.

### Reminder workflow (SRS rules #20, #21, #22)

- **Due date:** every `debt` carries `due_date`, set at sale time (`POST
  /sales`, from the request's `due_date` field) and editable via:

  **`PUT /debts/{id}/due-date`** — Access: CEO, Seller (own store) — `{ "due_date": "2026-08-15" }`.

- **Automatic reminder generation:** a scheduled background process (not a
  user-invoked endpoint) runs at least daily, finds every `debt` with
  `due_date <= today` and `remaining_amount > 0`, and sends an SMS reminder to
  `customers.phone` (SRS rule #22). This requires a persisted reminder log
  that is **not yet part of the approved `DATABASE_DESIGN.md`** — see
  [§16](#16-known-gaps--follow-ups) before this is implemented.
- **Manual reminder trigger:**

  **`POST /debts/{id}/reminders/send`** — Access: CEO, Seller (own store) —
  request body empty; sends an on-demand SMS reminder for the debt outside
  the automatic daily run (e.g., "remind again now"). Same underlying
  logging dependency as above.
- **Reminder history:**

  **`GET /debts/{id}/reminders`** — Access: CEO, Seller (own store) — lists
  past reminders sent for the debt (channel, sent_at). Same dependency.
- **Errors (both endpoints):** `422` if the customer has no `phone` on file;
  `404` unknown debt.

---

## 12. Expenses

**Purpose:** Record operational expenses incurred at a store (SRS §4.7).

### `POST /expenses`

Access: CEO, Seller — Seller: **own store auto-assigned** (`store_id` not
accepted in the request body — SRS rule #12) · CEO: any store in own company
(`store_id` required in body) · Super Admin: full, via support session (§2.2, amended)

- **Request:**
  ```
  { "store_id": 12, "expense_type": "fuel" | "driver" | "loader" | "other",
    "amount": "50000.00", "description": "string", "date": "2026-07-06" }
  ```
  (`store_id` omitted for Seller callers.)
- **Response:** created expense.
- **Validation:** `amount` > 0; `expense_type` one of the four fixed values
  ([DATABASE_DESIGN.md §3.22](DATABASE_DESIGN.md#3-table--column-reference));
  `description` required.
- **Business rules:** **an expense recorded by a Seller automatically belongs
  to the Seller's assigned store** (SRS rule #12) — the field is never
  accepted from a Seller's request, only derived from their token.
- **Notes:** expenses are **immutable** once created in this version — no
  `PUT`/`DELETE`; correction/approval workflows are an explicit SRS Future
  Roadmap item (§4.7) and are out of scope here.

### `GET /expenses` / `GET /expenses/{id}`

Access: CEO, Seller — Seller: own store only · CEO: any store / company-wide · Super Admin: full, via support session (§2.2, amended)

- **Query (list):** `store_id` (CEO only), `expense_type`, `date_from`,
  `date_to`, `page`, `page_size`.
- **Business rules:** expenses are part of store financials and follow the
  financial-visibility rules (SRS §4.7) — a Seller can never list another
  store's expenses, including via `store_id` query manipulation (rejected
  server-side regardless of the query value).

---

## 13. Dashboard

**Purpose:** Provide an at-a-glance, role-based summary of the business (SRS §4.1, rule #13).

### `GET /dashboard`

Access: CEO, Seller — Seller: **own store scope** · CEO: **company-wide, all stores** · Super Admin: full, via support session (§2.2, amended)

- **Response (shape shared, data scope differs by role):**
  ```
  { "scope": "store" | "company",
    "today_sales_total": "0.00", "today_sales_count": 0,
    "month_revenue": "0.00", "month_expenses": "0.00",
    "debtors_count": 0, "debtors_total": "0.00",
    "top_products": [ { "product_id", "name", "quantity_sold", "revenue" } ],
    "top_debtors": [ { "customer_id", "full_name", "remaining" } ],
    "recent_operations": [ { "type": "sale"|"stock_in", "reference", "date", "amount" } ],
    "sales_chart": [ { "label": "2026-07-01", "value": "0.00" } ] }
  ```
- **Business rules:** the dashboard is role-based (SRS rule #13) — a CEO's
  response aggregates across every store in the company; a Seller's response
  is computed against their own `store_id` only, using exactly the same
  response shape so the frontend does not need role-specific rendering logic.
- **Notes:** no "low stock" widget is included — `products.min_quantity` was
  deliberately removed from the approved database design
  ([DATABASE_DESIGN.md §11](DATABASE_DESIGN.md#11-store-inventory-model)), so
  no reorder threshold exists to compute it against in this version.

---

## 14. Reports

**Purpose:** Provide summarized business information for decision-making
(SRS §4.10).

### `GET /reports/sales`

Access: CEO, Seller — Seller: own store only · CEO: any store / company-wide · Super Admin: full, via support session (§2.2, amended)

- **Query:** `store_id` (CEO only), `date_from`, `date_to`.
- **Response:** aggregated totals (`total_revenue`, `total_count`,
  `by_payment_status`) and a daily/weekly breakdown.

### `GET /reports/inventory`

Access: CEO, Seller — Seller: own store only, or cross-store **quantities**
only via [§7](#7-inventory) · CEO: any store / company-wide · Super Admin: full, via support session (§2.2, amended)

- **Response:** current `store_stock` levels for the resolved scope, by product.

### `GET /reports/debts`

Access: CEO, Seller — Seller: own store only · CEO: any store / company-wide · Super Admin: full, via support session (§2.2, amended)

- **Response:** outstanding balances grouped by customer and by status
  (`active`/`overdue`).

### `GET /reports/expenses`

Access: CEO, Seller — Seller: own store only · CEO: any store / company-wide · Super Admin: full, via support session (§2.2, amended)

- **Response:** totals grouped by `expense_type` and by date.

**Notes (all report endpoints):** this version returns **JSON only**. Excel/PDF
export formats and scheduled/automated reports are explicit SRS Future
Roadmap items (§8) — the pre-existing single-tenant implementation already
has `?format=excel|pdf` support, but that predates this SRS and is not
carried forward until export formats are promoted into confirmed scope. See
[§16](#16-known-gaps--follow-ups).

---

## 15. Settings

**Purpose:** Manage company-level configuration (SRS §4.11).

### `GET /settings` / `PUT /settings`

Access: CEO only — Seller: no access · CEO: full (own company) · Super Admin: **no access**

- **Request (PUT):** `{ "key": "string", "value": "string" }` (single
  key/value) or a batch `{ "settings": [ { "key", "value" } ] }`.
- **Response:** the company's current settings as a key/value map.
- **Business rules:** settings are isolated per company
  ([DATABASE_DESIGN.md §3.23](DATABASE_DESIGN.md#3-table--column-reference),
  unique `(company_id, key)`). Super Admin has **no** endpoint here: per SRS
  §3.1, company settings are business data, not platform administration, and
  the approved database design has no platform-level settings table — there
  is nothing for a Super Admin "settings" view to show.

---

## 16. Known Gaps & Follow-ups

These are the specific points where this specification could not be fully
grounded in the two approved documents without either inventing a rule or
making an interpretation call. None of them block the rest of this
specification, but each should be resolved — ideally via a
`DATABASE_DESIGN.md` follow-up revision — before the corresponding endpoint is
implemented.

1. **Missing reminder log table.** The confirmed SMS debt-reminder workflow
   (SRS rules #20–#22, [§11](#11-debts) above) needs a persisted record of
   reminders sent, to avoid duplicate sends and to power
   `GET /debts/{id}/reminders`. The approved `DATABASE_DESIGN.md` (24 tables)
   does not yet include such a table — though its own
   [§15 Future Extensibility](DATABASE_DESIGN.md#15-future-extensibility)
   already anticipated exactly this case: *"a `notifications` or
   `reminder_log` table (customer, channel, sent_at, related debt) can be
   added without touching `debts`/`customers`."* **Recommendation:** promote
   this into `DATABASE_DESIGN.md` as a new table (e.g. `debt_reminders`:
   `id`, `debt_id` FK, `channel`, `sent_at`, `status`) before implementing the
   reminder endpoints.
2. **`customer_type` value naming mismatch.** The approved
   `DATABASE_DESIGN.md §3.11` defines `customers.customer_type` as an enum
   with values `individual` / `company`. The SRS (as now amended) uses the
   terms **Individual** / **Legal Entity**. This specification uses the wire
   value `legal_entity` (matching the SRS's clearer terminology and avoiding
   overloading the word "company," which already means *tenant* everywhere
   else in this schema) — **not** the literal `company` value currently
   written in `DATABASE_DESIGN.md`. **Recommendation:** update
   `DATABASE_DESIGN.md §3.11` to rename the enum value from `company` to
   `legal_entity` in a follow-up revision so the two documents agree exactly.
3. **Sale cancellation has no dedicated endpoint.** SRS rule #19 is satisfied
   here by treating "cancellation before finalization" as a pure client-side,
   pre-submission concept (§9) rather than a server-side state transition,
   because the approved `sales` table has no draft/pending status column and
   the existing single-tenant implementation already creates sale documents
   atomically with no intermediate state. This is a reasonable reading, not
   an explicit instruction — flagged for confirmation.
4. **`barcode` / `image` are stored but not exposed as features.** Both
   columns exist in the approved `products` table (carried over from the
   pre-SRS implementation), but SRS §8 lists barcode-based lookup and product
   images as future/unconfirmed. This spec accepts/returns the two fields as
   plain optional data but defines no barcode-lookup or image-upload
   endpoint.
5. **No cash-refund mechanism for returns on fully-paid sales.** A
   [Sale Return](#post-salesidreturns) against a sale with no outstanding
   debt only restores inventory; no refund-type payment or negative-payment
   concept exists in the approved schema, so this specification does not
   define one.
6. **No manual stock adjustment endpoint.** `DATABASE_DESIGN.md §11`
   anticipates a future `movement_type = "adjustment"` for stocktake
   corrections, but no SRS rule confirms this feature yet, so
   [§7 Inventory](#7-inventory) exposes no write endpoint of any kind.
7. **No correction path for Stock In or Expenses.** Both are modeled as
   immutable once created (§8, §12); SRS lists "approval flows" for expenses
   only as a future extension, and defines no correction workflow for either
   module.
8. **Report export formats excluded.** Excel/PDF export existed in the
   pre-SRS implementation but is explicit SRS Future Roadmap (§8); `§14
   Reports` is JSON-only in this version.
9. **Customer debt write-off is undefined.** `§10 Customers`'
   `POST /customers/{id}/deactivate` blocks deactivation while any debt
   remains outstanding, but no endpoint exists to write off/forgive a debt —
   this was not requested and is not implied by any confirmed rule.

---

*End of specification. Pending review before any implementation (backend
code, FastAPI routes, SQL, or ORM models) begins.*
