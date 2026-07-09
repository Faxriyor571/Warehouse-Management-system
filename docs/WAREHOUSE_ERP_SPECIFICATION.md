# Warehouse ERP — Software Requirements Specification (SRS)

**Document status:** Draft v1.0
**Product:** Cloud-based Multi-Tenant Warehouse ERP for agricultural fertilizer distributors
**Audience:** Product owners, architects, backend/frontend engineers, QA, DevOps

> This document is the **single source of truth** for the project. All design,
> implementation, and testing decisions must trace back to a requirement stated
> here. Where a requirement is not covered by this document, it must be added
> here first before it is built.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [User Roles and Permissions](#3-user-roles-and-permissions)
4. [Business Modules](#4-business-modules)
5. [Business Rules](#5-business-rules)
6. [UI Principles](#6-ui-principles)
7. [Technical Architecture](#7-technical-architecture)
8. [Future Roadmap](#8-future-roadmap)
9. [Non-functional Requirements](#9-non-functional-requirements)
10. [Development Rules](#10-development-rules)

---

## 1. Project Overview

### 1.1 Project Purpose

The Warehouse ERP is a **cloud-based, multi-tenant** platform that allows
agricultural fertilizer distribution businesses to manage their inventory,
sales, customers, debts, expenses, and staff across one or more physical stores.

The platform is delivered as a single hosted application that serves many
independent companies at once. Each company operates in complete isolation from
every other company, while sharing the same deployed software and infrastructure.

The system is designed around the day-to-day reality of fertilizer distribution:
goods arrive in bulk, are stored across one or more stores, and are sold to
farmers and other customers — frequently on credit. The ERP tracks every bag and
every unit of currency from the moment stock enters a store to the moment a debt
is fully settled.

### 1.2 Target Users

The platform serves four distinct classes of user:

- **System Owner** (platform role: `super_admin`) — the owner/operator of the
  ERP platform itself. Exists above every company; not a tenant user. Onboards
  companies and their CEOs, and — amended 2026-07-09, superseding the original
  "management only" restriction below — can reach every store, employee,
  report, dashboard, setting, inventory record, sale, debt, and expense in any
  company, for platform administration, customer support, troubleshooting,
  and QA. See §2.2 and §3.1.
- **Company (tenant)** — an individual distribution business subscribing to the
  platform.
- **CEO** — the owner/top manager inside a company, with visibility across all of
  that company's stores.
- **Seller** — a store-level operator who performs daily sales, stock, and
  expense operations for a single assigned store.

End customers (farmers and buyers) are **not** users of the system; they are
records managed within it.

### 1.3 Business Goals

- Provide accurate, real-time inventory across all of a company's stores.
- Automate the calculation of stock quantities and outstanding debt so that
  operators never have to compute balances by hand.
- Give store sellers a fast, mobile-first workflow that minimizes manual data
  entry and reduces the number of taps needed to complete a sale.
- Give the CEO a consolidated, company-wide view of performance, inventory, and
  outstanding debt across every store.
- Guarantee strict data isolation between companies so the platform can be sold
  as a service to many independent businesses.
- Support offline-tolerant, installable usage on phones through PWA capabilities.

---

## 2. System Architecture

### 2.1 Multi-Tenant Architecture

The platform is **multi-tenant**: a single deployed instance of the application
and database serves many companies. Every business record in the system belongs
to exactly one company, and **every company can access only its own data**.

Tenancy is enforced at the data-access layer: every query for company-owned data
is scoped by the requesting user's company. There is no supported path through
which one company can read or write another company's records.

The tenancy hierarchy is:

```
System Owner  (platform level)
   └── Company  (tenant)
          └── CEO  (company owner)
                 └── Seller  (store-level operator)
                        └── Store  (physical location the seller is assigned to)
```

### 2.2 System Owner (Super Admin)

> **Amended 2026-07-09.** This section previously restricted the Super Admin
> to platform management only, with no access to any company's business data.
> That restriction is superseded by explicit product decision: the System
> Owner requires full operational access to every company for platform
> administration, customer support, troubleshooting, and QA. The role name in
> code and the database (`super_admin`) is unchanged — "System Owner" is the
> product-facing name for the same role.

The System Owner operates at the platform level, above every individual
company, and is **not a tenant user** — it belongs to no company
(`company_id IS NULL`, unconditionally). The System Owner:

- Creates companies and their first CEO account.
- Manages the lifecycle of companies (activation status).
- Can access every company, every store, every employee, every report, every
  dashboard, every setting, every inventory record, every sale, every debt,
  and every expense, across the entire platform.

That access is implemented as an explicit, deliberate **support session**: the
System Owner opens a session scoped as the CEO-equivalent of one company at a
time (`POST /companies/{id}/support-session`), rather than every module
silently trusting a blanket "is platform admin" flag. A CEO already has full
access to everything within their company, so this satisfies the requirement
exactly, through the same, already-correct CEO-scoped code path every module
uses. The session is short-lived (expires with the normal access-token TTL,
no refresh token), and every action taken during it is attributed in the
audit log to the real System Owner, not a fabricated identity. The System
Owner's own identity (outside of a support session) has no route into any
company's operational data — only the Companies module (§4.1) and the support
session mechanism itself.

### 2.3 Company

A Company is a tenant of the platform — one independent fertilizer distribution
business. All of the company's stores, products, customers, sales, stock
movements, expenses, debts, and employees live inside the company's isolated data
boundary. A company may operate one or many stores.

### 2.4 CEO

The CEO is the top-level user inside a company. The CEO **can access every store**
belonging to their company, including all inventory and all financial information
for those stores. The CEO has the company-wide, consolidated view of the business.

### 2.5 Seller

A Seller is a store-level operator. A seller is assigned to a single store and
**can access only their assigned store** for operational work. A seller performs
the store's daily operations: sales, stock intake, expenses, and customer/debt
handling for that store.

A seller **can see the inventory quantities of other stores** (for example, to
know whether another store has a product in stock), but **cannot see the financial
information of other stores**.

---

## 3. User Roles and Permissions

The platform uses **Role-Based Access Control (RBAC)**. Each user is assigned a
role, and each role grants a defined set of capabilities. Access is further
constrained by tenancy (company isolation) and, for sellers, by store assignment.

| Role             | Scope                              | Can access other companies | Can access all stores in own company | Financial visibility |
|------------------|-------------------------------------|----------------------------|---------------------------------------|-----------------------|
| System Owner     | Platform (every company)           | Yes (full, via support session — amended 2026-07-09) | N/A (belongs to no company) | Full, any company (via support session) |
| CEO              | Entire own company                 | No                         | Yes                                   | All own-company stores |
| Seller           | Single assigned store              | No                         | No (inventory quantities only)        | Own store only        |

### 3.1 System Owner permissions

*Amended 2026-07-09 — see §2.2 for the full rationale and mechanism.*

- Onboard companies and create their first CEO account.
- Manage the lifecycle of companies (activation status).
- Open a support session into any company, scoped as that company's CEO —
  granting full access to its stores, employees, catalogue, customers, stock
  in, sales, debts, expenses, inventory, dashboard, reports, and settings, for
  platform administration, customer support, troubleshooting, and QA.
- Every support-session action is audit-logged under the System Owner's real
  identity.
- Has no standing access to any company's business data outside of an
  actively open support session.

### 3.2 CEO permissions

- Full visibility and control over **all stores** in the company.
- Access to all inventory and **all financial information** across every store.
- Manage company-level configuration and employees (sellers).
- View company-wide dashboards and reports.

### 3.3 Seller permissions

- Operate a **single assigned store** only.
- Perform sales, stock in, expenses, returns, and customer/debt operations for
  the assigned store.
- **See inventory quantities of other stores**, but **not their financial data**.
- View a store-scoped, role-based dashboard limited to the assigned store.

### 3.4 Permission enforcement principles

- Every data access is scoped by company (tenant isolation).
- Seller data access is additionally scoped by assigned store, except for the
  explicit allowance to view other stores' inventory quantities.
- Financial information of a store is visible only to the CEO (company-wide) and
  to the seller assigned to that store (own store only).

---

## 4. Business Modules

Every module below is described in terms of its **Purpose**, **Users**,
**Business rules**, **Main UI**, and **Future extensions**. Only confirmed rules
are stated; anything marked as a future extension is explicitly out of the
current committed scope.

### 4.1 Dashboard

- **Purpose:** Provide an at-a-glance summary of the business, tailored to the
  role of the signed-in user.
- **Users:** CEO (company-wide view), Seller (assigned-store view).
- **Business rules:**
  - The dashboard is **role-based**: the content and scope of the dashboard
    depend on the user's role.
  - The CEO sees a company-wide view spanning all stores.
  - The seller sees a view scoped to their assigned store.
- **Main UI:** A mobile-first landing screen of summary cards. Card view is the
  default presentation.
- **Future extensions:** Additional charts and trend widgets, configurable
  dashboard layouts.

### 4.2 Products

- **Purpose:** Maintain the catalogue of fertilizer products that the company
  buys, stores, and sells.
- **Users:** CEO (all stores), Seller (assigned store operations; can view other
  stores' quantities).
- **Business rules:**
  - Products belong to the company (tenant isolation).
  - Stock quantity per product is **calculated automatically** from stock
    movements (stock in, sales, returns).
  - One bag equals 50 kg; product quantities are handled consistently with this
    conversion.
  - Sellers can see the inventory quantities of a product across other stores,
    but not the financial information of other stores.
- **Main UI:** Card view by default (product cards with quantity), with an
  optional table view. Fast search.
- **Future extensions:** Barcode-based lookup, product images, richer categorization.

### 4.3 Stores

- **Purpose:** Represent the physical stores (locations) operated by the company.
- **Users:** CEO (all stores), Seller (assigned store).
- **Business rules:**
  - A company may operate one or many stores.
  - Each seller is assigned to a single store and operates only that store.
  - The CEO can access every store in the company.
  - Sellers can view other stores' inventory quantities but not their financials.
- **Main UI:** Store list/cards; store detail showing inventory (and financials
  only where the viewer is permitted).
- **Future extensions:** Inter-store transfer workflows.

### 4.4 Customers

- **Purpose:** Maintain records of the farmers and buyers the company sells to,
  including their outstanding debt.
- **Users:** CEO (company-wide), Seller (assigned store).
- **Business rules:**
  - Customers belong to the company (tenant isolation).
  - A customer's outstanding **debt is calculated automatically** from sales and
    payments.
  - Every customer has a **customer type**: **Individual** or **Legal Entity**.
    The customer type determines the pricing rule applied at sale time (see
    §4.6 Sales).
- **Main UI:** Customer cards/list with quick access to balance and history;
  customer detail with purchase and debt history.
- **Future extensions:** Customer contact actions (call, general messaging)
  beyond the confirmed SMS debt-reminder notifications (see §4.8 Debts).

### 4.5 Stock In

- **Purpose:** Record incoming goods that arrive at a store.
- **Users:** CEO (all stores), Seller (assigned store).
- **Business rules:**
  - **Stock In increases inventory** for the store receiving the goods.
  - Quantities follow the 1 bag = 50 kg convention.
  - Stock movements are scoped to the store where they occur (tenant + store
    isolation).
- **Main UI:** A fast intake form (mobile-first) with minimal manual input.
- **Future extensions:** Supplier-linked intake, purchase-order matching.

### 4.6 Sales

- **Purpose:** Record sales of products to customers, including sales made on
  credit (debt).
- **Users:** CEO (all stores), Seller (assigned store).
- **Business rules:**
  - **Sales decrease inventory** of the selling store.
  - **Returns restore inventory using the original sale price.**
  - Debt arising from credit sales is **calculated automatically**.
  - Quantities follow the 1 bag = 50 kg convention.
  - Sales are scoped to the seller's assigned store.
  - **Sale cancellation:** a sale **may be cancelled only before it has been
    finalized**. A sale that has already been completed **cannot** be
    cancelled — reversing it must be done through a **Sale Return** instead
    (see Returns, above). Inventory and financial records must remain fully
    consistent under either path.
  - **Legal entity pricing:** **Individual** customers are always sold at the
    product's default selling price. Sellers **may override the selling price
    only when the customer's type is Legal Entity** (see §4.4 Customers).
    Sales to Individual customers never accept a price override.
- **Main UI:** A fast sales workflow optimized for the fewest possible clicks;
  card-based product selection; mobile-first.
- **Future extensions:** Printable/shareable receipts, discounts and promotions.

### 4.7 Expenses

- **Purpose:** Record operational expenses incurred at a store.
- **Users:** CEO (all stores), Seller (assigned store).
- **Business rules:**
  - An expense recorded by a seller **automatically belongs to the seller's
    assigned store**.
  - Expenses are part of the store's financial information and follow the
    financial-visibility rules (CEO company-wide; seller own store only).
- **Main UI:** A simple expense entry form with minimal manual input.
- **Future extensions:** Expense categories and approval flows.

### 4.8 Debts

- **Purpose:** Track outstanding customer debt and its repayment.
- **Users:** CEO (company-wide), Seller (assigned store).
- **Business rules:**
  - Debt is **calculated automatically** from credit sales and recorded payments.
  - Returns affect balances consistently with the original sale price.
  - Debt information is part of store financials and follows the
    financial-visibility rules.
  - Every debt record includes an **expected payment date (due date)**.
  - The system **generates a reminder notification when a debt's due date
    arrives**, for any debt not yet fully paid.
  - **SMS notification support is a core requirement**: debt due-date
    reminders are delivered to the customer via SMS.
- **Main UI:** Debt list/cards with outstanding balances; per-customer debt and
  payment history.
- **Future extensions:** Additional reminder channels beyond SMS (e.g. call,
  in-app push notifications).

### 4.9 Employees

- **Purpose:** Manage the company's staff — primarily sellers and their store
  assignments.
- **Users:** CEO.
- **Business rules:**
  - Employees belong to the company (tenant isolation).
  - Each seller is assigned to a single store, which scopes their operational
    access.
- **Main UI:** Employee list with store assignment; create/edit seller accounts.
- **Future extensions:** Finer-grained per-employee permissions, activity views.

### 4.10 Reports

- **Purpose:** Provide summarized business information for decision making.
- **Users:** CEO (company-wide), Seller (assigned store, where permitted).
- **Business rules:**
  - Report scope follows role and tenancy: the CEO sees company-wide reports;
    a seller sees reports for their assigned store.
  - Financial reporting follows the financial-visibility rules.
- **Main UI:** Summary cards and lists optimized for mobile; drill-down where
  useful.
- **Future extensions:** Export formats, scheduled reports, richer analytics.

### 4.11 Settings

- **Purpose:** Manage company- and user-level configuration.
- **Users:** System Owner (platform/company lifecycle, and any company's
  settings via a support session — §2.2), CEO (own company settings).
- **Business rules:**
  - Company settings are isolated per tenant.
  - Configuration options must respect the platform's tenancy and role model.
- **Main UI:** A simple, grouped settings screen.
- **Future extensions:** Localization, notification preferences, theme options.

---

## 5. Business Rules

The following are the confirmed, authoritative business rules for the platform.
No additional business rules may be assumed or invented; anything not listed here
must be added to this document before it is implemented.

1. **Multi-tenant (company isolation):** The platform is multi-tenant, with each
   company isolated from every other company.
2. **Own-data access only:** Every company can access only its own data.
3. **Seller store scope:** Sellers can access only their assigned store.
4. **Cross-store inventory visibility:** Sellers can see the inventory quantities
   of other stores, but **not** their financial information.
5. **CEO store access:** The CEO can access every store in the company.
6. **Automatic stock quantity:** Stock quantity is calculated automatically.
7. **Automatic debt:** Debt is calculated automatically.
8. **Unit conversion:** One bag = 50 kg.
9. **Stock In:** Stock In increases inventory.
10. **Sales:** Sales decrease inventory.
11. **Returns:** Returns restore inventory using the original sale price.
12. **Expense ownership:** Expenses belong automatically to the seller's assigned
    store.
13. **Role-based dashboard:** The dashboard is role-based.
14. **Mobile-first design:** The application is designed mobile-first.
15. **PWA support:** The application supports Progressive Web App capabilities.
16. **Simple UI:** The UI is simple, with minimal manual input.
17. **Customer type:** Every customer is classified as either **Individual** or
    **Legal Entity**.
18. **Legal entity pricing override:** Sellers may override a product's selling
    price **only** when selling to a Legal Entity customer; Individual-customer
    sales always use the default selling price.
19. **Sale cancellation:** A sale may be cancelled only before it is finalized.
    A completed sale can only be reversed via a Sale Return, never cancelled.
20. **Debt due date:** Every debt record includes an expected payment (due)
    date.
21. **Debt reminders:** The system generates a reminder notification when a
    debt's due date arrives.
22. **SMS notifications:** SMS delivery of debt due-date reminders is a core
    platform requirement.

---

## 6. UI Principles

The user interface is designed for fast, low-friction operation on phones used in
the field, while remaining fully usable on larger screens.

- **Mobile First:** The interface is designed for mobile screens first, then
  scaled up to larger devices.
- **Card View as default:** Lists are presented as cards by default, which read
  well on small screens.
- **Table View optional:** A table view is available as an optional presentation
  where a denser layout is useful.
- **Responsive:** Layouts adapt cleanly across phone, tablet, laptop, and desktop.
- **Fast workflow:** Common operations (especially sales) are optimized for speed.
- **Minimal clicks:** Workflows are designed to require as few taps/clicks as
  possible, with minimal manual input.

---

## 7. Technical Architecture

The technologies below are the recommended stack for the platform.

### 7.1 Frontend

- **React** — component-based UI library.
- **TypeScript** — static typing for reliability and maintainability.
- **Vite** — build tool and development server.
- **Tailwind CSS** — utility-first styling for a consistent, responsive UI.
- **shadcn/ui** — accessible, composable UI component patterns.
- **TanStack Query** — server-state management, caching, and data fetching.

### 7.2 Backend

- **FastAPI** — Python web framework for the API layer.
- **SQLAlchemy** — ORM for data access.
- **PostgreSQL** — relational database.
- **Alembic** — database schema migrations.
- **SMS Gateway integration** — required for delivering debt due-date reminder
  notifications (core requirement, §4.8 Debts).

### 7.3 Deployment

- **Docker** — containerized packaging of the application.
- **Nginx** — reverse proxy / static asset serving.
- **Ubuntu** — server operating system for hosting.

### 7.4 PWA

- The frontend is delivered as a **Progressive Web App**, allowing installation
  on devices and supporting a mobile-first, app-like experience.

### 7.5 Architectural principles

- Tenant isolation is enforced at the data-access layer for all company-owned
  data.
- Derived values — stock quantity and debt — are computed by the system rather
  than entered by hand.
- The API is role-aware and enforces both role permissions and tenancy/store
  scoping on every request.

---

## 8. Future Roadmap

The following items are explicitly **future** work and are not part of the
current confirmed scope. They are recorded here so that the current design can
accommodate them, but they must not be implemented until promoted into the
confirmed requirements.

- Customer contact actions (call, general messaging) beyond the confirmed SMS
  debt-reminder notifications.
- Barcode-based product lookup and product images.
- Printable/shareable sales receipts.
- Inter-store inventory transfers.
- Expense categories and approval workflows.
- Report export formats and scheduled/automated reports.
- Localization and additional UI theming (including dark mode).
- Finer-grained, per-employee permission customization.

---

## 9. Non-functional Requirements

- **Security & isolation:** Strict multi-tenant data isolation; a company must
  never be able to access another company's data. Role- and store-based access
  control is enforced on every request.
- **Data integrity:** Derived quantities (stock, debt) must always be consistent
  with the underlying movements (stock in, sales, returns, payments).
- **Performance & responsiveness:** The UI must remain fast and responsive on
  mobile devices, with workflows optimized for minimal clicks.
- **Availability:** As a cloud-hosted, multi-company service, the platform should
  be deployable and operable as a continuously available service.
- **Scalability:** The architecture must support many companies (tenants) and
  many stores per company on shared infrastructure.
- **Usability:** Simple UI with minimal manual input, suitable for field use on
  phones.
- **Offline tolerance / installability:** PWA support enables an installable,
  app-like experience.
- **Maintainability:** A typed frontend and a clearly layered backend keep the
  codebase maintainable as scope grows.
- **Portability:** Containerized deployment (Docker) on a standard Ubuntu/Nginx
  stack for predictable hosting.

---

## 10. Development Rules

- **This document is authoritative.** It is the single source of truth for the
  project. Implementation must follow it.
- **Do not invent business rules.** Only the confirmed rules in
  [Section 5](#5-business-rules) may be implemented. Any new rule must be added
  to this document first.
- **Preserve backend contracts.** Read the actual backend schema/API before
  building against it; do not assume fields or endpoints that are not defined.
- **No duplicate code.** Reuse existing architecture and shared components.
- **Tenancy and scope are non-negotiable.** Company isolation, seller store
  scope, and the financial-visibility rules must be enforced everywhere.
- **Mobile-first, minimal input.** All UI work must honor the UI principles in
  [Section 6](#6-ui-principles).
- **Honest verification reporting.** Only claim what was actually executed. If a
  build, type-check, or test suite was not run, state **"Not executed in my
  environment."** Never fabricate build, test, or verification results.
- **Scope discipline.** Items in the [Future Roadmap](#8-future-roadmap) are out
  of scope until explicitly promoted into the confirmed requirements.

---

*End of specification.*
