# TECHWANDO — Multilingual Martial Arts, Sports Education & Club Management Platform

**TECHWANDO** is a modular, security-hardened, production-oriented **Django 5.2 LTS** web platform and **REST API (`/api/v1/`)** built for an international martial arts academy and sports club operating natively in **Persian (`fa-IR`, RTL)** and **Japanese (`ja-JP`, LTR)**.

It integrates three isolated yet connected surfaces:
1. **Multilingual Public Website & SEO Showcase** — Academy overview, educational curriculum, martial arts training programs, official equipment catalog (no online checkout), bilingual blog, verified Champions directory with search/filtering/sorting, public Athlete Profiles, Medal Winners honor roll, Belt Achievements registry, Competition Results, and anti-spam Contact form.
2. **Private Club Member Portal** — Individual athlete dashboard for personal profile & privacy consent, sports achievements, championship medals (Gold/Silver/Bronze/Special), belt promotion history, competition participations, social/community activities, protected certificate uploads, moderation feedback, formal correction requests, notifications, and account settings.
3. **Role-Based Administration Portal & Customized Django Admin** — Unified moderation queue, membership application approval/rejection, member account activation/deactivation, belt rank & competition configuration, bilingual blog/product/page/SEO editors, contact inbox, moderation history (`ReviewLog`), and immutable security `AuditLog`s.

---

## Architecture & Directory Structure

```text
techwando/
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── config/
│   ├── settings/
│   │   ├── base.py          # Shared configuration, Argon2, i18n (fa/ja), DRF, logging
│   │   ├── development.py   # Local development settings
│   │   ├── production.py    # Hardened HTTPS/HSTS/cookie/proxy/Sentry settings
│   │   └── testing.py       # Fast isolated in-memory test settings
│   ├── urls.py              # Localized /fa/ & /ja/ i18n_patterns + /api/v1/ + SEO + media guards
│   ├── sitemaps.py          # Multilingual XML sitemaps (static, pages, blog, products, champions)
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── core/                # Base models, ReviewLog, ModerationService, RBAC mixins,
│   │                        # PrivateMediaStorage, file validators, CSP middleware,
│   │                        # Persian/Japanese template tags, and management commands
│   ├── accounts/            # Custom email User model, 5 RBAC roles/groups, rate-limited auth,
│   │                        # custom admin dashboard, unified moderation queue & member admin
│   ├── members/             # MemberProfile, privacy consent, member portal & public Champions views
│   ├── achievements/        # Moderated sports achievements + private certificates
│   ├── belts/               # Configurable BeltType ranks + moderated BeltHistory promotions
│   ├── medals/              # Moderated Gold/Silver/Bronze/Other medals + private evidence
│   ├── activities/          # Moderated social/community activities + consent-gated photos
│   ├── competitions/        # Official Competition events + moderated CompetitionParticipation
│   ├── blog/                # Category, Tag, Post + unique (post, language) PostTranslation
│   ├── products/            # ProductCategory, Product (SKU, optional price), ProductImage + translations
│   ├── pages/               # Page (About/Education/Service/Policy) + PageTranslation
│   ├── seo/                 # SEOMetadata + SEOTranslation + robots.txt
│   ├── contact/             # Anti-spam ContactMessage + admin review inbox
│   ├── notifications/       # Localized in-app Notification + NotificationService
│   ├── audit_logs/          # Immutable AuditLog + log_audit_event service
│   └── api/                 # Versioned /api/v1/ DRF ViewSets, serializers, permissions & OpenAPI
├── templates/               # Semantic RTL/LTR HTML5 templates (public, accounts, member, admin)
├── static/                  # Design system CSS (techwando.css, rtl.css, ja.css), JS, SVG assets
├── locale/                  # Compiled Persian (fa) and Japanese (ja) gettext catalogs (.po/.mo)
├── tests/                   # Automated test suite (auth, RBAC, moderation, i18n/SEO, API, security)
├── deploy/                  # Gunicorn, Nginx (HTTPS + X-Accel-Redirect), systemd, backup cron, logrotate
└── docs/                    # Deployment guide, SQLite backup/restore guide, security checklist
```

---

## Multilingual & Database Design

- **Interface Localization**: Persian (`fa`, `dir="rtl"`, Vazirmatn typography, Persian numerals `۰۱۲۳۴۵۶۷۸۹`, Jalali-friendly formatting) and Japanese (`ja`, `dir="ltr"`, Noto Sans JP typography, `YYYY年M月D日` dates, family-name-first ordering, balanced CJK line-height) with distinct typography rules—never a naive layout mirror.
- **Database Translation Pattern**: Content entities (`Post`, `Category`, `Product`, `ProductCategory`, `Page`, `SEOMetadata`) store language-neutral attributes once and pair with dedicated `*Translation` tables enforcing `UniqueConstraint(fields=[<parent>, "language"])`, with automatic fallback when a language variant is not yet authored.
- **Database Compatibility**: Default `db.sqlite3` (WAL mode + `PRAGMA foreign_keys=ON`) using 100% standard Django ORM models/constraints ready for zero-redesign migration to PostgreSQL.

---

## Roles & Access Control (RBAC)

| Role | Scope |
|---|---|
| `SUPER_ADMIN` | Full platform, role assignment, all admin modules, audit logs, and Django Admin. |
| `CONTENT_ADMIN` | Blog/categories, products/categories, pages/programs, bilingual translations, SEO metadata, contact inbox. |
| `CLUB_MANAGER` | Member management, membership application approvals/rejections, account activation, submission moderation, belt ranks, competitions, contact inbox, review & audit logs. |
| `MODERATOR` | Moderation queue review (approve/reject/needs-revision) for achievements, medals, belts, competitions, and social activities; contact inbox. |
| `MEMBER` | Private member portal only, strictly isolated to their own `MemberProfile`, submissions, certificates, and notifications. |

---

## Key Localized Routes & REST API (`/api/v1/`)

### Web Routes (available under both `/fa/...` and `/ja/...`)
- Public: `/fa/`, `/fa/about/`, `/fa/education/`, `/fa/services/`, `/fa/blog/`, `/fa/products/`, `/fa/champions/`, `/fa/champions/<slug>/`, `/fa/champions/medals/`, `/fa/champions/belts/`, `/fa/champions/competitions/`, `/fa/contact/`
- Auth: `/fa/accounts/login/`, `/fa/accounts/register/`, `/fa/accounts/password-reset/`
- Member Portal: `/fa/member/dashboard/`, `/fa/member/profile/`, `/fa/member/achievements/`, `/fa/member/medals/`, `/fa/member/belts/`, `/fa/member/competitions/`, `/fa/member/activities/`, `/fa/member/notifications/`, `/fa/member/settings/`
- Administration: `/fa/accounts/management/`, `/fa/accounts/management/moderation/`, `/fa/accounts/management/members/`, `/django-admin/` (configurable via `DJANGO_ADMIN_URL`)
- SEO & Ops: `/robots.txt`, `/sitemap.xml`, `/healthz/`

### REST API (`/api/v1/`, Session Auth + CSRF, localized via `Accept-Language: fa|ja`)
- **OpenAPI Docs**: `/api/v1/schema/`, `/api/v1/docs/` (Swagger UI), `/api/v1/redoc/`
- **Public**: `GET /api/v1/public/{blog,products,champions,medals,pages}/`, `POST /api/v1/public/contact/`
- **Member**: `GET|PATCH /api/v1/member/profile/`, CRUD + `POST .../request_correction/` on `/api/v1/member/{achievements,medals,belts,activities}/`, `GET|POST /api/v1/member/notifications/`
- **Admin**: `/api/v1/admin/members/` (+ `POST .../review/`), `/api/v1/admin/{medals,achievements,belts,activities}/` (+ `POST .../review/`), CRUD on `/api/v1/admin/{posts,products,pages}/`

---

## Quickstart & Exact Commands

```bash
# 1. Create virtual environment & install dependencies
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 2. Configure environment (optional for local dev; required for production)
cp .env.example .env

# 3. Apply database migrations & sync RBAC role groups
.venv/bin/python manage.py migrate
.venv/bin/python manage.py setup_roles

# 4. Compile Persian (fa) & Japanese (ja) gettext translations
.venv/bin/python manage.py compile_translations

# 5. (Optional) Seed bilingual content, belt ranks, competitions & demo accounts
.venv/bin/python manage.py seed_techwando --with-demo-accounts

# 6. Create a real Super Admin account
.venv/bin/python manage.py createsuperuser

# 7. Run the development server
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

### Testing, Security Audit & Operations Commands

```bash
# Run the complete automated test suite (49 tests across auth, RBAC, moderation, i18n, SEO, API & security)
DJANGO_SETTINGS_MODULE=config.settings.testing .venv/bin/python manage.py test tests apps --verbosity=2

# Verify zero unapplied model changes
.venv/bin/python manage.py makemigrations --check --dry-run

# Run Django production deployment security audit
DJANGO_SETTINGS_MODULE=config.settings.production \
  DJANGO_SECRET_KEY="$(.venv/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" \
  DJANGO_ALLOWED_HOSTS="techwando.example.com" \
  DJANGO_CSRF_TRUSTED_ORIGINS="https://techwando.example.com" \
  SITE_BASE_URL="https://techwando.example.com" \
  .venv/bin/python manage.py check --deploy

# Collect static files for production
.venv/bin/python manage.py collectstatic --noinput

# Run verified online SQLite backup with SHA-256 checksum & retention pruning
.venv/bin/python manage.py backup_sqlite --output-dir ./backups --keep 14
```

### Local Demo Accounts (only when seeded with `--with-demo-accounts`)

Default demo password (override via `--demo-password`): `Techwando!2026`
- Super Admin: `admin@techwando.example.com`
- Content Admin: `content@techwando.example.com`
- Club Manager: `manager@techwando.example.com`
- Moderator: `moderator@techwando.example.com`
- Private Member (with pending submission): `member@techwando.example.com`
- Verified Public Champions: `arash.rezaei@techwando.example.com`, `haruka.sato@techwando.example.com`, `parisa.moradi@techwando.example.com`, `kenji.takahashi@techwando.example.com`

> Never use `--with-demo-accounts` in production.

---

## Further Documentation

- [Production Deployment Guide (Docker, Gunicorn, Nginx, HTTPS & PostgreSQL Migration)](docs/deployment.md)
- [SQLite Online Backup, Verification & Disaster Recovery Guide](docs/sqlite-backup-restore.md)
- [Security Architecture & Pre-Launch Checklist](docs/security-checklist.md)
