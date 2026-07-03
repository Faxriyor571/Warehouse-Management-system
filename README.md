# Ombor Boshqaruv Tizimi (Warehouse Management System)

Kichik korxonalar uchun professional, production-ready ombor boshqaruv tizimi.
Mahsulot kirimi/chiqimi, qarz nazorati, hisobotlar va rol asosidagi ruxsatlar (RBAC).

## Texnologiyalar

| Qatlam | Texnologiya |
|--------|-------------|
| Backend | Python 3.13+, FastAPI |
| Frontend | Jinja2, HTML5, CSS3, Bootstrap 5, JavaScript |
| Ma'lumotlar bazasi | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migratsiya | Alembic |
| Auth | JWT, bcrypt (passlib) |
| Server | Uvicorn |

## Loyiha strukturasi

```
wms/
├── app/
│   ├── config.py          # Sozlamalar (.env dan)
│   ├── database.py        # Engine, session, Base
│   ├── models/            # SQLAlchemy modellari
│   ├── schemas/           # Pydantic sxemalari (validatsiya)
│   ├── crud/              # Ma'lumotlar bazasi CRUD amallari
│   ├── services/          # Biznes logika (kirim, chiqim, qarz, ...)
│   ├── routers/           # FastAPI endpointlar
│   ├── auth/              # JWT, parol hashlash, dependency
│   ├── permissions/       # RBAC ruxsatlari
│   ├── middleware/        # Middleware (audit, xatolik)
│   ├── utils/             # Yordamchi funksiyalar
│   ├── templates/         # Jinja2 shablonlar
│   └── static/            # CSS / JS / rasm
├── alembic/               # Migratsiyalar
├── tests/                 # Testlar (pytest)
├── docs/                  # Hujjatlar (ER diagram, ...)
├── uploads/               # Yuklangan fayllar (mahsulot rasmlari)
├── logs/                  # Log fayllari
├── requirements.txt
├── .env.example
└── docker-compose.yml
```

## O'rnatish (lokal ishga tushirish)

### 1. Repozitoriyni klonlash va virtual muhit

```bash
git clone <repo-url>
cd wms
python3.13 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Sozlamalar

```bash
cp .env.example .env
# .env faylini oching va qiymatlarni to'ldiring (ayniqsa SECRET_KEY va DB parol).
python -c "import secrets; print(secrets.token_urlsafe(64))"   # SECRET_KEY uchun
```

### 3. PostgreSQL

Docker orqali (tavsiya etiladi):

```bash
docker compose up -d
```

Yoki mahalliy PostgreSQL da `wms_db` bazasini va `wms_user` foydalanuvchisini yarating.

### 4. Migratsiya (ixtiyoriy)

Ilova ishga tushganda kerakli jadvallar avtomatik yaratiladi (`create_all`) va
boshlang'ich ma'lumotlar (rollar, ruxsatlar, admin, to'lov turlari, birliklar)
seed qilinadi. Ishlab chiqarish (production) uchun Alembic tavsiya etiladi:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 5. Ishga tushirish

```bash
uvicorn app.main:app --reload
```

- Ilova: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Sog'lomlik: http://localhost:8000/health

**Boshlang'ich admin** (`.env` dan sozlanadi): `admin` / `Admin12345!`
Kirgach parolni albatta o'zgartiring.

### 6. Testlar

```bash
pytest
```

Testlar xotiradagi SQLite'da ishlaydi — tashqi baza talab qilmaydi.

## Ishlab chiqish bosqichlari

- [x] 1-bosqich — Database (modellar, ER diagram, migratsiya sozlamasi)
- [x] 2-bosqich — Authentication (JWT, bcrypt, refresh, me)
- [x] 3-bosqich — RBAC / Permissions (rollar, ruxsatlar, dependency)
- [x] 4-bosqich — Admin panel (users, roles, settings, payment methods)
- [x] 5-bosqich — Mahsulotlar (CRUD, barcode, rasm, filtr)
- [x] 6-bosqich — Yetkazib beruvchilar
- [x] 7-bosqich — Fermerlar / mijozlar (qarz xulosasi, tarix)
- [x] 8-bosqich — Kirim (ombor avtomatik oshadi)
- [x] 9-bosqich — Chiqim (ombor kamayadi, aralash to'lov, qarz)
- [x] 10-bosqich — Qarzdorlar (qisman to'lov, tarix)
- [x] 11-bosqich — Hisobotlar (Excel/PDF eksport)
- [x] 12-bosqich — Dashboard (statistika, grafiklar) + Eslatmalar
- [ ] 13-bosqich — Responsive UI (Jinja2/Bootstrap — keyingi bosqich)
- [x] 14-bosqich — Testlar (pytest, SQLite)

## REST API (asosiy endpointlar)

Barcha endpointlar `/api/v1` prefiksi ostida. Autentifikatsiya: `Authorization: Bearer <token>`.

| Guruh | Endpoint |
|-------|----------|
| Auth | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` |
| Users | `GET/POST /users`, `PUT/DELETE /users/{id}`, `POST /users/{id}/reset-password`, `/activate`, `/deactivate` |
| Profile | `PUT /profile`, `POST /profile/change-password` |
| Roles | `GET/POST /roles`, `PUT/DELETE /roles/{id}`, `GET /permissions` |
| Katalog | `/categories`, `/units`, `/products` (CRUD, `/products/barcode/{code}`, `/products/{id}/image`) |
| Kontragent | `/suppliers`, `/customers` (`GET /customers/{id}` — qarz + tarix) |
| Operatsiya | `POST/GET /stock-in`, `POST/GET /stock-out` |
| To'lov/Qarz | `/payment-methods`, `/debts`, `POST /debts/{id}/payments` |
| Eslatma | `GET /reminders`, `GET /reminders/call-list` |
| Insight | `GET /dashboard`, `/reports/*` (`?format=excel|pdf`), `GET /audit-logs` |

Batafsil ma'lumotlar bazasi sxemasi: [`docs/ER_DIAGRAM.md`](docs/ER_DIAGRAM.md).
