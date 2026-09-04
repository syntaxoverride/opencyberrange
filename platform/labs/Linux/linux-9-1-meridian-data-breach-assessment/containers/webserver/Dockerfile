FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# ── Directory structure ──────────────────────────────────────────────────
RUN mkdir -p /var/www/html/staff \
             /var/www/html/notices \
             /var/www/html/policies \
             /var/www/html/contact \
             /var/www/html/backups/legacy

# ── Intranet pages ───────────────────────────────────────────────────────
COPY index.html /var/www/html/index.html
COPY staff.html /var/www/html/staff/index.html
COPY notices.html /var/www/html/notices/index.html
COPY policies.html /var/www/html/policies/index.html
COPY contact.html /var/www/html/contact/index.html

# ── Legacy backup directory (misconfigured. accessible without auth) ────
COPY legacy_index.html /var/www/html/backups/legacy/index.html
COPY meridian_dump.sql /var/www/html/backups/legacy/meridian_dump.sql
COPY migration_notes.txt /var/www/html/backups/legacy/migration_notes.txt

# ── nginx configuration ─────────────────────────────────────────────────
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
