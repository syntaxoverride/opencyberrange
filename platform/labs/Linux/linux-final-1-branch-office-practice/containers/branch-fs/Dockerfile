FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba \
    snmpd \
    snmp \
    && rm -rf /var/lib/apt/lists/*

# Samba user for restricted dispatch-backups share
RUN useradd -M -s /usr/sbin/nologin dispatch_svc && \
    printf 'B4ckup_Atl4s_2024#\nB4ckup_Atl4s_2024#\n' | smbpasswd -a -s dispatch_svc

# Public share: branch-shared (guest, contains the IT handover doc that leaks creds)
RUN mkdir -p /srv/samba/branch-shared && \
    printf 'ATLAS DISTRIBUTION\n\
CORPUS CHRISTI BRANCH OFFICE\n\
=============================\n\
\n\
Welcome to the Corpus Christi branch file server.\n\
\n\
This server hosts shared documents for branch operations.\n\
For IT support, the corporate help desk is at extension 4400.\n\
\n\
Please remember: customer shipping records and financial\n\
data must NOT be stored on this server. Use the corporate\n\
SharePoint instance for any sensitive material.\n\
\n\
- Atlas IT Department\n' > /srv/samba/branch-shared/welcome.txt && \
    printf 'CORPUS CHRISTI BRANCH. PHONE DIRECTORY\n\
========================================\n\
\n\
Branch Manager       Karen Vogel        ext. 4100\n\
Operations Lead      Marcus Reilly      ext. 4200\n\
Dispatch Supervisor  Linda Yates        ext. 4300\n\
Help Desk Liaison    (vacant)           ext. 4400\n\
Receiving Floor      Hector Diaz        ext. 4500\n\
Driver Pool          (rotating)         ext. 4600\n\
\n\
Last updated: 2025-08-12\n' > /srv/samba/branch-shared/phone_directory.txt && \
    printf 'BRANCH IT HANDOVER NOTES\n\
==========================\n\
Date: 2025-09-30\n\
Author: Brian Holm, Branch IT Administrator (departing)\n\
\n\
This document covers the systems I was responsible for\n\
during my time at the Corpus Christi branch. Please file\n\
a ticket with corporate IT to take over these systems.\n\
\n\
1. FILE SERVER (this host, atlas-ccx-fs01)\n\
   - Two Samba shares: branch-shared (guest) and\n\
     dispatch-backups (restricted to dispatch_svc account).\n\
   - Service account credentials for dispatch-backups:\n\
       username: dispatch_svc\n\
       password: B4ckup_Atl4s_2024#\n\
     This account is used by the nightly backup cron job\n\
     on the portal server. Please rotate the password\n\
     after I leave.\n\
\n\
2. INTRANET PORTAL (atlas-ccx-portal, .11)\n\
   - Custom Flask application I wrote for ticket tracking.\n\
   - Public site is at the root URL.\n\
   - Staff login is at /staff-portal/ but the link is\n\
     intentionally kept off the navigation. The path is\n\
     also listed in robots.txt for search engine\n\
     suppression.\n\
   - Please port this to the corporate ticketing system\n\
     in Q1 2026.\n\
\n\
3. SNMP\n\
   - Both hosts have SNMP enabled with the default public\n\
     community string. The sysContact field has the asset\n\
     code corporate uses to track this hardware.\n\
\n\
Sorry for the rough handoff. Six years was a good run.\n\
- Brian\n' > /srv/samba/branch-shared/IT_Handover_Notes.txt && \
    chmod -R 755 /srv/samba/branch-shared

# Restricted share: dispatch-backups (requires dispatch_svc credentials)
RUN mkdir -p /srv/samba/dispatch-backups && \
    printf 'BRANCH STATUS REPORT. CORPUS CHRISTI\n\
========================================\n\
Reporting period: 2025-Q3\n\
Generated: 2025-10-01\n\
Document control token=h4rv3st\n\
\n\
Daily dispatch volume:        avg 187 packages\n\
Late delivery rate:           3.2 percent\n\
Driver-hours billed:          4,210\n\
Customer complaints:          12 (resolved)\n\
\n\
Backup status:\n\
- Nightly job last completed at 02:15 local.\n\
- Off-site replication is two days behind schedule.\n\
- Restore drills are overdue. Last drill was Q1 2025.\n\
\n\
Notes:\n\
- Receiving floor scanner failed twice this quarter.\n\
- Replacement requested but not yet approved.\n\
\n\
- Linda Yates, Dispatch Supervisor\n' > /srv/samba/dispatch-backups/branch_status_report.txt && \
    printf 'BACKUP JOB LOG. ROLLING\n\
==========================\n\
2025-10-25  02:14:08  STARTED   nightly_dispatch_backup\n\
2025-10-25  02:15:42  OK        17,492 files copied\n\
2025-10-26  02:14:09  STARTED   nightly_dispatch_backup\n\
2025-10-26  02:15:51  OK        17,503 files copied\n\
2025-10-27  02:14:08  STARTED   nightly_dispatch_backup\n\
2025-10-27  02:15:48  OK        17,511 files copied\n\
2025-10-28  02:14:09  STARTED   nightly_dispatch_backup\n\
2025-10-28  02:16:02  OK        17,520 files copied\n\
\n\
End of log.\n' > /srv/samba/dispatch-backups/backup_job.log && \
    chown -R dispatch_svc:dispatch_svc /srv/samba/dispatch-backups && \
    chmod -R 770 /srv/samba/dispatch-backups

# Samba configuration
RUN printf '[global]\n\
   workgroup = ATLAS-CCX\n\
   server string = Atlas Corpus Christi Branch File Server\n\
   security = user\n\
   map to guest = Bad User\n\
   log file = /var/log/samba/log.%%m\n\
   max log size = 50\n\
   server min protocol = NT1\n\
\n\
[branch-shared]\n\
   path = /srv/samba/branch-shared\n\
   browseable = yes\n\
   read only = yes\n\
   guest ok = yes\n\
   comment = Branch shared documents\n\
\n\
[dispatch-backups]\n\
   path = /srv/samba/dispatch-backups\n\
   browseable = yes\n\
   read only = yes\n\
   guest ok = no\n\
   valid users = dispatch_svc\n\
   comment = Dispatch backup archive\n' > /etc/samba/smb.conf

# SNMP configuration: recon flag in sysContact
RUN printf '# Atlas Distribution Branch File Server SNMP\n\
\n\
rocommunity public\n\
\n\
sysDescr    Atlas Distribution Branch File Server\n\
sysLocation Atlas Distribution / Corpus Christi Branch / Server Room A\n\
sysContact  Branch IT (corporate-it@atlasdistribution.com) | Asset token=atl4s\n\
sysName     atlas-ccx-fs01\n\
\n\
agentAddress udp:161\n\
\n\
view all included .1\n\
rouser noAuthUser\n' > /etc/snmp/snmpd.conf

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 139 445 161/udp

CMD ["/start.sh"]
