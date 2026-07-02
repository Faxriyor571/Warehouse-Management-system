# Database ER Diagram — Ombor Boshqaruv Tizimi

Bu hujjat ma'lumotlar bazasi sxemasini tavsiflaydi. Diagramma [Mermaid](https://mermaid.js.org/)
formatida yozilgan (GitHub uni avtomatik render qiladi).

## Umumiy tamoyillar

- **Normalization**: 3NF ga muvofiq. Takrorlanuvchi ma'lumotlar alohida jadvallarga ajratilgan.
- **Foreign Keys**: barcha bog'lanishlar FK bilan ta'minlangan, mos `ondelete` qoidalari bilan.
- **Indexes**: tez-tez qidiriladigan/filtrlanadigan ustunlar (`sku`, `barcode`, `phone`, `date`,
  `status`, FK lar) indekslangan.
- **Cascade**: hujjat qatorlari (`stock_in_items`, `stock_out_items`, `payments`, `debt_payments`)
  ota yozuv o'chirilganda `CASCADE` bilan o'chadi. Ma'lumotnoma jadvallariga (`products`,
  `categories`, `units`, ...) `RESTRICT` qo'yilgan — noto'g'ri o'chirishning oldini oladi.
- **Soft Delete**: `users`, `products`, `categories`, `suppliers`, `customers` da `deleted_at`
  ustuni bor — yozuvlar fizik o'chirilmasdan "arxivlanadi".
- **Money/Qty**: pul `NUMERIC(14,2)`, miqdor `NUMERIC(14,3)` (kg kabi kasrli birliklar uchun).

## Diagramma

```mermaid
erDiagram
    ROLES ||--o{ USERS : "assigned to"
    ROLES }o--o{ PERMISSIONS : "role_permissions"
    USERS ||--o{ STOCK_INS : "created_by"
    USERS ||--o{ STOCK_OUTS : "created_by"
    USERS ||--o{ PAYMENTS : "created_by"
    USERS ||--o{ DEBTS : "created_by"
    USERS ||--o{ DEBT_PAYMENTS : "created_by"
    USERS ||--o{ AUDIT_LOGS : "performed"

    CATEGORIES ||--o{ PRODUCTS : "has"
    UNITS ||--o{ PRODUCTS : "measured in"

    SUPPLIERS ||--o{ STOCK_INS : "supplies"
    STOCK_INS ||--o{ STOCK_IN_ITEMS : "contains"
    PRODUCTS ||--o{ STOCK_IN_ITEMS : "listed in"

    CUSTOMERS ||--o{ STOCK_OUTS : "buys"
    STOCK_OUTS ||--o{ STOCK_OUT_ITEMS : "contains"
    PRODUCTS ||--o{ STOCK_OUT_ITEMS : "listed in"
    STOCK_OUTS ||--o{ PAYMENTS : "paid by"
    PAYMENT_METHODS ||--o{ PAYMENTS : "used in"

    STOCK_OUTS ||--o| DEBTS : "may create"
    CUSTOMERS ||--o{ DEBTS : "owes"
    DEBTS ||--o{ DEBT_PAYMENTS : "repaid by"
    PAYMENT_METHODS ||--o{ DEBT_PAYMENTS : "used in"

    ROLES {
        int id PK
        string name UK
        string description
        bool is_system
    }
    PERMISSIONS {
        int id PK
        string code UK
        string name
        string group
    }
    USERS {
        int id PK
        string username UK
        string email UK
        string full_name
        string hashed_password
        int role_id FK
        bool is_active
        bool is_superuser
        datetime last_login_at
        datetime deleted_at
    }
    CATEGORIES {
        int id PK
        string name UK
        bool is_active
        datetime deleted_at
    }
    UNITS {
        int id PK
        string name UK
        string short_name
        bool is_active
    }
    PRODUCTS {
        int id PK
        string name
        string sku UK
        string barcode UK
        int category_id FK
        int unit_id FK
        numeric purchase_price
        numeric sale_price
        numeric min_quantity
        numeric quantity
        string image
        bool is_active
        datetime deleted_at
    }
    SUPPLIERS {
        int id PK
        string name
        string phone
        string address
        string responsible_person
        datetime deleted_at
    }
    CUSTOMERS {
        int id PK
        string full_name
        string phone
        string address
        string passport
        datetime deleted_at
    }
    STOCK_INS {
        int id PK
        string reference UK
        int supplier_id FK
        int created_by_id FK
        datetime date
        numeric total_amount
    }
    STOCK_IN_ITEMS {
        int id PK
        int stock_in_id FK
        int product_id FK
        numeric quantity
        numeric price
        numeric subtotal
    }
    STOCK_OUTS {
        int id PK
        string reference UK
        int customer_id FK
        int created_by_id FK
        datetime date
        numeric subtotal
        numeric discount
        numeric total_amount
        numeric paid_amount
        string payment_status
    }
    STOCK_OUT_ITEMS {
        int id PK
        int stock_out_id FK
        int product_id FK
        numeric quantity
        numeric price
        numeric discount
        numeric subtotal
    }
    PAYMENT_METHODS {
        int id PK
        string name UK
        string type
        bool is_active
        bool is_system
    }
    PAYMENTS {
        int id PK
        int stock_out_id FK
        int payment_method_id FK
        int created_by_id FK
        numeric amount
        datetime date
    }
    DEBTS {
        int id PK
        int customer_id FK
        int stock_out_id FK
        int created_by_id FK
        numeric amount
        numeric paid_amount
        numeric remaining_amount
        date start_date
        date due_date
        string status
    }
    DEBT_PAYMENTS {
        int id PK
        int debt_id FK
        int payment_method_id FK
        int created_by_id FK
        numeric amount
        datetime date
    }
    SETTINGS {
        int id PK
        string key UK
        string value
    }
    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string entity_type
        int entity_id
        string ip_address
        datetime created_at
    }
```

## Jadvallar ro'yxati (18 ta)

| # | Jadval | Tavsif |
|---|--------|--------|
| 1 | `roles` | Rollar (admin, manager, ...) |
| 2 | `permissions` | Mayda ruxsatlar (product.create, ...) |
| 3 | `role_permissions` | Rol–ruxsat bog'lanishi (M:N) |
| 4 | `users` | Foydalanuvchilar |
| 5 | `categories` | Mahsulot kategoriyalari |
| 6 | `units` | O'lchov birliklari |
| 7 | `products` | Mahsulotlar |
| 8 | `suppliers` | Yetkazib beruvchilar |
| 9 | `customers` | Fermerlar / mijozlar |
| 10 | `stock_ins` | Kirim hujjatlari |
| 11 | `stock_in_items` | Kirim qatorlari |
| 12 | `stock_outs` | Chiqim (savdo) hujjatlari |
| 13 | `stock_out_items` | Chiqim qatorlari |
| 14 | `payment_methods` | To'lov turlari |
| 15 | `payments` | Savdo to'lovlari (aralash to'lov) |
| 16 | `debts` | Qarzlar |
| 17 | `debt_payments` | Qarz to'lovlari tarixi |
| 18 | `settings` | Tizim sozlamalari (key/value) |
| 19 | `audit_logs` | Audit jurnali |
