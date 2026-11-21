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
├── static/                  # Design-system CSS (variables/layout/components/forms/responsive/
│                            # dashboard/rtl/ja), vanilla JS, local Bootstrap 5 & Bootstrap Icons,
│                            # Vazirmatn + Noto Sans JP woff2, SVG logos & image placeholders
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
- Public: `/fa/`, `/fa/about/`, `/fa/education/`, `/fa/services/`, `/fa/privacy/`, `/fa/terms/`, `/fa/blog/`, `/fa/blog/<slug>/`, `/fa/products/`, `/fa/products/<slug>/`, `/fa/champions/`, `/fa/champions/<public-slug>/`, `/fa/champions/medals/`, `/fa/champions/belts/`, `/fa/champions/competitions/`, `/fa/contact/`
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
# Run the complete automated test suite (59 tests across auth, RBAC, moderation, i18n, SEO, API, security & frontend templates)
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
- Private Member (with a pending medal submission): `member@techwando.example.com`
- Verified Public Champions: `parisa.rahimi@techwando.example.com`, `haruto.yamamoto@techwando.example.com`, `amir.hosseini@techwando.example.com`, `aoi.nakamura@techwando.example.com`

> Never use `--with-demo-accounts` in production.

---

## Further Documentation

- [Production Deployment Guide (Docker, Gunicorn, Nginx, HTTPS & PostgreSQL Migration)](docs/deployment.md)
- [SQLite Online Backup, Verification & Disaster Recovery Guide](docs/sqlite-backup-restore.md)
- [Security Architecture & Pre-Launch Checklist](docs/security-checklist.md)

---

## Frontend Design System (Bootstrap 5, RTL/LTR)

The interface is server-rendered with **Django templates + HTML5 + CSS3 + Bootstrap 5.3.3 + Bootstrap Icons + vanilla JavaScript**. No React/Vue/Angular/Next.js/Tailwind/jQuery is used. Bootstrap, Bootstrap Icons and Vazirmatn are served locally from `static/vendor/` and `static/fonts/`, so pages render without any CDN request.

### Structure

```text
templates/
├── base.html                 # <html lang dir>, SEO/OG metadata, skip link, navbar, messages, modal
├── includes/                 # navbar, footer, messages, pagination, breadcrumbs, form_fields,
│                             # status_badge, medal_badge, page_header, empty_state, stat_card,
│                             # cta, modal, sidebar_member, sidebar_admin, review_history
├── public/                   # home, about, education, services, legal/privacy/terms, blog_*,
│                             # product_*, champions_list, champion_detail, medal_winners,
│                             # belt_achievements, competition_results, contact, page_detail
├── accounts/                 # login, register, password reset flow
├── dashboard/
│   ├── base_member.html      # sidebar + mobile offcanvas shell
│   ├── base_admin.html       # administration shell
│   ├── member/               # overview, profile_edit, achievements, belts, medals,
│   │                         # competitions, activities, notifications, delete/correction
│   └── admin/                # overview, moderation queue/review, members, content CRUD,
│                             # SEO, contact inbox, audit logs
├── 403.html / 404.html / 500.html
└── emails/
```

```text
static/
├── css/
│   ├── variables.css         # design tokens (brand palette, spacing, radius, shadows, fonts)
│   ├── layout.css            # header, hero, sections, cards, footer, page banner, grid
│   ├── components.css        # buttons, badges, alerts, tables, cards, pagination, timeline
│   ├── forms.css             # inputs, validation, uploads, auth, error summary
│   ├── dashboard.css         # sidebar/offcanvas shell, KPI cards, dashboard helpers
│   ├── responsive.css        # 320/576/768/992/1200/1440 breakpoints, print, contrast
│   ├── rtl.css               # Persian-only typographic and icon corrections
│   ├── ja.css                # Japanese-only CJK typography
│   └── main.css              # imports the cascade in order
├── js/
│   ├── main.js               # theme, password toggle, image preview, confirm modal, alerts
│   └── dashboard.js          # offcanvas link closing, table affordance, filter submit
├── vendor/bootstrap/         # Bootstrap 5.3.3 LTR + RTL + bundle (local)
├── vendor/bootstrap-icons/   # icon font + CSS (local)
├── fonts/                    # Vazirmatn woff2 (Persian) + Noto Sans JP woff2 (Japanese)
└── images/                   # logo, default avatar, OG image, placeholders
```

`base.html` loads `bootstrap.rtl.min.css` + `rtl.css` when `IS_RTL`, otherwise
`bootstrap.min.css` + `ja.css`. Design tokens live in `variables.css`; retheming the
whole site only requires editing that file.

### Frontend conventions

- **Escaping and URLs**: always `{% url %}`, `{% static %}`, `{% csrf_token %}`, `{% trans %}`/`{% blocktrans %}`. Never hardcode Persian/Japanese interface copy.
- **Permission-aware UI**: hide member/admin navigation with `IS_ADMIN_PORTAL_USER`, `IS_CLUB_MANAGER`, `IS_CONTENT_ADMIN`; backend mixins remain the source of truth.
- **Privacy**: never render `PRIVATE_MEDIA_ROOT` `.url` values; use the protected `get_certificate_url` / `get_evidence_url` endpoints. Public champion cards only use approved + consented records.
- **Forms**: include `includes/form_fields.html` inside `<form novalidate>`; it renders labels, help text, validation errors, `aria-invalid`/`aria-describedby`, password toggles and local image previews.
- **Empty states**: every queryset loop is guarded with `{% empty %}` or `{% include "includes/empty_state.html" %}` so seeded-less databases still render.
- **JavaScript**: progressive enhancement only; all navigation, forms and logout work with JS disabled. Confirm dialogs use a Bootstrap modal and fall back to native confirmation.
- **Bootstrap RTL**: use logical properties (`margin-inline-start`, `border-inline-start`, `inline-size`) in custom CSS instead of left/right.
- **Adding a string**: wrap it in `{% trans %}`, run `python manage.py compile_translations`, and add `msgstr` entries to `locale/fa` and `locale/ja` `django.po`.

### Frontend QA checklist

```bash
# 1. Django configuration and templates
python manage.py check --settings=config.settings.development

# 2. Full test suite (templates, permissions, CSRF, i18n/SEO)
python manage.py test --settings=config.settings.testing

# 3. Compile catalogs after editing .po files
python manage.py compile_translations

# 4. Run and inspect key routes
python manage.py runserver 0.0.0.0:8000
# /fa/  /ja/  /fa/champions/  /fa/blog/  /fa/products/  /fa/contact/
# /fa/accounts/login/  /fa/member/dashboard/  /fa/accounts/management/
```

Responsive breakpoints to verify in browser devtools: **320px, 768px, 1024px, 1440px**.
Tables scroll horizontally inside `.table-wrap`; the member sidebar becomes an
offcanvas drawer below 992px. Check both `dir="rtl"` (`/fa/`) and `dir="ltr"` (`/ja/`),
keyboard focus rings, skip link, and contrast in light/dark themes.
