FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba \
    && rm -rf /var/lib/apt/lists/*

# ── Samba user for restricted share ──────────────────────────────────
RUN useradd -M -s /usr/sbin/nologin hr_svc && \
    printf 'Bl4ckw3ll_HR#\nBl4ckw3ll_HR#\n' | smbpasswd -a -s hr_svc

# ── Public share: "general" ─────────────────────────────────────────
RUN mkdir -p /srv/samba/general && \
    printf '3num\n' > /srv/samba/general/token.txt && \
    printf 'BLACKWELL & ASSOCIATES. NEW EMPLOYEE ONBOARDING\n\
=====================================================\n\
\n\
Welcome to Blackwell & Associates. Please review the following:\n\
\n\
1. Workstation setup: Contact IT (ext. 4401)\n\
2. Email: Your credentials will be sent separately\n\
3. File server access:\n\
   - General share: No credentials needed\n\
   - HR share: Contact HR department\n\
     Service account for HR portal integration:\n\
     Username: hr_svc\n\
     Password: Bl4ckw3ll_HR#\n\
     (TODO: Move to password manager before Q4 audit. Victoria)\n\
4. VPN: Request through IT helpdesk\n\
\n\
Questions? Contact your team lead or IT support.\n' > /srv/samba/general/onboarding_notes.txt && \
    printf 'Blackwell & Associates File Server\n\
Updated: September 2024\n\
Contact: it@blackwell-law.com\n' > /srv/samba/general/README.txt && \
    chmod -R 755 /srv/samba/general

# ── Restricted share: "hr_data" ─────────────────────────────────────
RUN mkdir -p /srv/samba/hr_data && \
    printf 'sh4r3d\n' > /srv/samba/hr_data/assessment_token.txt && \
    printf 'Employee ID,Name,Department,Salary\n\
1001,Victoria Blackwell,Executive,285000\n\
1002,Robert Chen,Litigation,195000\n\
1003,Sarah Martinez,Corporate Law,178000\n\
1004,David Kim,IP Law,165000\n\
1005,Amanda Foster,HR,92000\n' > /srv/samba/hr_data/employee_records.csv && \
    chown -R hr_svc:hr_svc /srv/samba/hr_data && \
    chmod -R 770 /srv/samba/hr_data

# ── Samba configuration ─────────────────────────────────────────────
RUN printf '[global]\n\
   workgroup = BLACKWELL\n\
   server string = Blackwell File Server\n\
   security = user\n\
   map to guest = Bad User\n\
   log file = /var/log/samba/log.%%m\n\
   max log size = 50\n\
\n\
[general]\n\
   path = /srv/samba/general\n\
   browseable = yes\n\
   read only = yes\n\
   guest ok = yes\n\
   comment = General Documents\n\
\n\
[hr_data]\n\
   path = /srv/samba/hr_data\n\
   browseable = yes\n\
   read only = yes\n\
   guest ok = no\n\
   valid users = hr_svc\n\
   comment = HR Department Files\n' > /etc/samba/smb.conf

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 139 445

CMD ["/start.sh"]
