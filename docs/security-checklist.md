# TECHWANDO Security Architecture & Pre-Production Checklist

## 1. Implemented Security Controls

| Domain | Implementation |
|---|---|
| **Authentication & Passwords** | Custom email-based `User` model; **Argon2** primary password hasher (`Argon2PasswordHasher`) with PBKDF2 fallback; Django password validators (min length 10, similarity, common, numeric); POST-only logout with CSRF; session rotation on login/password change. |
| **Brute-Force & Abuse Defense** | Dual-key login rate limiting (IP + IP:email, HTTP `429` lockout + security log); contact form rate limiting + hidden honeypot field; DRF `AnonRateThrottle`, `UserRateThrottle`, and `ScopedRateThrottle` (`contact: 5/hour`). |
| **RBAC & Object Isolation** | 5 explicit roles (`SUPER_ADMIN`, `CONTENT_ADMIN`, `CLUB_MANAGER`, `MODERATOR`, `MEMBER`) mapped to Django `Group`s & granular `Permission`s; server-side view mixins (`MemberRequiredMixin`, `ContentAdminMixin`, `ClubManagerMixin`, `ModeratorMixin`, `SuperAdminMixin`) and DRF permission classes; all member queries scoped strictly to `request.user`'s own `MemberProfile`. |
| **Privilege-Escalation Prevention** | Public registration hard-codes `UserRole.MEMBER` and `MembershipStatus.PENDING`; member forms/serializers mark `approval_status`, `admin_note`, `reviewer`, `reviewed_at`, `membership_number`, and `role` immutable; self-approval blocked in `ModerationService`, API, and Django Admin bulk actions; only `SUPER_ADMIN` can assign or edit privileged roles. |
| **Private File Protection** | Certificates, medal evidence, and private activity photographs use `PrivateMediaStorage` rooted at `PRIVATE_MEDIA_ROOT` (outside `MEDIA_ROOT`), randomized UUID filenames (`RandomizedUploadTo`), blocked `.url()` (`SuspiciousOperation`), permission-checked delivery views (`ProtectedSubmissionFileView`) with path-traversal check, `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store`, Nginx `internal` `X-Accel-Redirect`, and explicit 403 block on `/media/(certificates\|medals\|activities)/`. |
| **Upload Validation** | `SafeImageValidator` & `SafeDocumentValidator`: size cap (`MAX_UPLOAD_SIZE_MB`), extension allowlist (`.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`), magic-byte header verification, Pillow decompression-bomb/dimension/decode verification, and rejection of PDFs containing `/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFile`, or `/OpenAction`. |
| **Athlete Privacy & Consent** | Public Champions, Medal Winners, Belt Achievements, Competition Results, Sitemaps, and `/api/v1/public/` require `user.is_active=True`, `membership_status=APPROVED`, `public_profile_consent=True`, `public_profile_visibility=True`, and record `approval_status=APPROVED`. Email, phone number, birth date, admin notes, and certificates are never rendered or serialized on public endpoints. |
| **XSS, CSRF, SQLi & Open Redirect** | Auto-escaped Django templates (zero unescaped user HTML); CSRF middleware on all HTML forms and DRF `SessionAuthentication` (no stateless JWT in localStorage); 100% parameterized Django ORM queries; `url_has_allowed_host_and_scheme` on login `next` and language switcher redirects. |
| **Transport & HTTP Headers** | `config/settings/production.py` enforces `DEBUG=False`, `SECURE_SSL_REDIRECT`, 1-year `HSTS` (`includeSubDomains`, `preload`), `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS="DENY"`, `SECURE_CONTENT_TYPE_NOSNIFF`, `Content-Security-Policy`, `Referrer-Policy`, and `Permissions-Policy`. |
| **Auditability** | Immutable `audit_logs.AuditLog` (actor, IP, user-agent, action, model, metadata) and `core.ReviewLog` (full moderation state transition history) with add/edit/delete disabled in Django Admin. |

---

## 2. Pre-Launch Security Checklist

- [ ] `DJANGO_SETTINGS_MODULE=config.settings.production` and `DJANGO_DEBUG=False` verified.
- [ ] `python manage.py check --deploy` returns **0 errors and 0 warnings**.
- [ ] Unique 50+ character `DJANGO_SECRET_KEY` loaded from `.env` (mode `0600`), never committed to Git.
- [ ] `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` restricted to exact production domains.
- [ ] `DJANGO_ADMIN_URL` changed from default `/django-admin/` to a non-guessable path.
- [ ] No demo accounts (`--with-demo-accounts`) created on production database; real `SUPER_ADMIN` uses a strong unique passphrase.
- [ ] `db.sqlite3` stored outside web root with `0600` permissions; automated `backup_sqlite` cron and off-site replication tested.
- [ ] `private_media/` has mode `0750`, is mounted read-only into Nginx under `location /_private_media/ { internal; }`, and `USE_X_ACCEL_REDIRECT=True`.
- [ ] TLS 1.2/1.3 certificate active with automatic Certbot renewal and HTTP-to-HTTPS 301 redirect verified.
- [ ] Full automated test suite (`DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py test`) passes 100%.
