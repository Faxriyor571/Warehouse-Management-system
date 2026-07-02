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

### 4. Migratsiya

```bash
# Birinchi migratsiyani yaratish (modellardan avtomatik):
alembic revision --autogenerate -m "initial schema"
# Bazaga qo'llash:
alembic upgrade head
```

### 5. Ishga tushirish

```bash
uvicorn app.main:app --reload
```

Ilova: http://localhost:8000 · API hujjatlari: http://localhost:8000/docs

## Ishlab chiqish bosqichlari

- [x] 1-bosqich — Database (modellar, ER diagram, migratsiya sozlamasi)
- [ ] 2-bosqich — Authentication (JWT, bcrypt)
- [ ] 3-bosqich — RBAC / Permissions
- [ ] 4-bosqich — Admin panel
- [ ] 5-bosqich — Mahsulotlar
- [ ] 6-bosqich — Yetkazib beruvchilar
- [ ] 7-bosqich — Fermerlar / mijozlar
- [ ] 8-bosqich — Kirim
- [ ] 9-bosqich — Chiqim
- [ ] 10-bosqich — Qarzdorlar
- [ ] 11-bosqich — Hisobotlar
- [ ] 12-bosqich — Dashboard
- [ ] 13-bosqich — Responsive UI
- [ ] 14-bosqich — Testlar

Batafsil ma'lumotlar bazasi sxemasi: [`docs/ER_DIAGRAM.md`](docs/ER_DIAGRAM.md).
