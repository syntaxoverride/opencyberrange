FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba \
    snmpd \
    snmp \
    && rm -rf /var/lib/apt/lists/*

# Samba user for restricted phi-archive share
RUN useradd -M -s /usr/sbin/nologin clinic_archivist && \
    printf 'Arch1ve_P1n3_2024#\nArch1ve_P1n3_2024#\n' | smbpasswd -a -s clinic_archivist

# Public share: clinic-shared
RUN mkdir -p /srv/samba/clinic-shared && \
    printf 'PINECREST FAMILY PRACTICE\n\
INTERNAL FILE SERVER\n\
=============================\n\
\n\
Welcome to the Pinecrest Family Practice file server.\n\
\n\
This server hosts shared documents for clinic operations.\n\
\n\
Patient health information (PHI) must NOT be stored here.\n\
PHI access is governed by our HIPAA workflow and goes through\n\
MyChart and the EHR system, not this file server.\n\
\n\
For IT support: please contact the practice manager.\n\
- Pinecrest Family Practice\n' > /srv/samba/clinic-shared/welcome.txt && \
    printf 'PINECREST FAMILY PRACTICE. PROVIDER DIRECTORY\n\
==============================================\n\
\n\
Dr. Helena Yasin           Family Medicine     ext. 101\n\
Dr. Marcus Brennan         Pediatrics          ext. 102\n\
Dr. Aisha Patel-Rao        Internal Medicine   ext. 103\n\
Dr. Theo Wei               Family Medicine     ext. 104\n\
Dr. Devin Lassiter         Geriatrics          ext. 105\n\
Sandra Pham, NP            Adult Primary Care  ext. 106\n\
Renee Patel                Practice Manager    ext. 200\n\
Marcus Linton              Office Coordinator  ext. 201\n\
\n\
Last updated: 2025-09-12\n' > /srv/samba/clinic-shared/provider_directory.txt && \
    printf 'CLINIC HOURS\n\
=============\n\
\n\
Monday      7:30 AM. 5:30 PM\n\
Tuesday     7:30 AM. 5:30 PM\n\
Wednesday   7:30 AM. 7:00 PM (extended)\n\
Thursday    7:30 AM. 5:30 PM\n\
Friday      7:30 AM. 4:00 PM\n\
Saturday    9:00 AM. 12:00 PM (urgent only)\n\
Sunday      Closed\n\
\n\
Emergency contact: 911 or visit the nearest emergency department.\n\
After-hours nurse line: (704) 555-0166\n' > /srv/samba/clinic-shared/clinic_hours.txt && \
    printf 'IT NOTES. PINECREST FAMILY PRACTICE\n\
=====================================\n\
Author: Reggie Coombs, IT Vendor (Stillwater Tech LLC)\n\
Last entry: 2025-07-30\n\
\n\
Pinecrest dropped our service contract effective 2025-07-31.\n\
This document is being left on the file server for whoever\n\
takes over IT next so they have a starting point. The clinic\n\
manager has a copy of all administrator passwords in the\n\
locked filing cabinet under the front desk.\n\
\n\
=== File server (this host, pinecrest-fs01) ===\n\
- Two Samba shares: clinic-shared (open to staff) and\n\
  phi-archive (locked down to clinic_archivist).\n\
- The phi-archive share holds quarterly compliance reports\n\
  that the previous compliance officer used to track audit\n\
  findings. The share is restricted because the reports\n\
  reference patients by name.\n\
- clinic_archivist credentials: password is Arch1ve_P1n3_2024#\n\
  This account was created by me; please rotate after handoff.\n\
  In case you have not worked with smbclient before, here is the\n\
  one-liner to log into the restricted share:\n\
    smbclient //<ip>/phi-archive -U clinic_archivist%Arch1ve_P1n3_2024#\n\
\n\
=== Staff portal (pinecrest-staff) ===\n\
- Internal scheduling tool I built for the front desk.\n\
- Login is at /staff/ on port 80. The path is hidden from\n\
  the navigation and from search engines via robots.txt.\n\
- The application has no patient data; it is just shift\n\
  scheduling and ticketing. Pinecrest decided not to use\n\
  it after switching to MyChart but left it running.\n\
- I recommended decommissioning the staff portal at the\n\
  end of our contract. The clinic manager said it would\n\
  be addressed by the next IT vendor.\n\
\n\
=== Network ===\n\
- SNMP is enabled on the file server. Asset tag for\n\
  the corporate equipment lease is set in the sysContact\n\
  field with the public community string.\n\
\n\
=== Outstanding items ===\n\
- Upgrade Samba to a supported version (current build is OK\n\
  but EOL in 2026).\n\
- Migrate phi-archive contents to the EHR vendor.\n\
- Decommission staff portal.\n\
\n\
- Reggie\n' > /srv/samba/clinic-shared/IT_Notes_2025.txt && \
    chmod -R 755 /srv/samba/clinic-shared

# Restricted share: phi-archive (requires clinic_archivist credentials)
RUN mkdir -p /srv/samba/phi-archive && \
    printf 'COMPLIANCE PHI BREACH SUMMARY. INTERNAL\n\
=========================================\n\
Reporting period: 2025-Q2\n\
Compliance officer: Vacant (position eliminated 2025-05)\n\
Document control Token 2 = l34k\n\
\n\
Q2 2025 Privacy and Security Findings\n\
\n\
1. Two access logs from the EHR vendor were not retained for\n\
   the required six year period. Cause: backup retention rule\n\
   was misconfigured during the 2024 vendor migration.\n\
   Severity: Medium. Status: Resolved 2025-06.\n\
\n\
2. One mailing of patient appointment reminders was sent to\n\
   an outdated address list. Twelve letters returned to\n\
   sender. No PHI disclosed to incorrect recipients.\n\
   Severity: Low. Status: Resolved 2025-05.\n\
\n\
3. Front desk staff observed leaving an unlocked workstation\n\
   during lunch. Verbal coaching delivered. Workstation\n\
   inactivity timeout reduced from 15 to 5 minutes.\n\
   Severity: Low. Status: Resolved 2025-04.\n\
\n\
4. Receiving fax line printed twelve unsolicited prescription\n\
   refill requests intended for a different practice. Faxes\n\
   shredded; sender notified.\n\
   Severity: Informational. Status: Resolved 2025-04.\n\
\n\
No reportable breaches under HIPAA Breach Notification Rule\n\
during the reporting period.\n\
\n\
- Pinecrest Compliance, formerly\n' > /srv/samba/phi-archive/phi_breach_summary.txt && \
    printf 'PATIENT ACCESS LOG SAMPLE. REDACTED\n\
=====================================\n\
Generated: 2025-06-30\n\
\n\
This file is a sample export from the EHR audit log,\n\
included with the Q2 compliance summary as evidence of\n\
log review. All patient identifiers have been replaced\n\
with sequential placeholders.\n\
\n\
2025-06-29 08:14  PT-0001  appointment-view    Dr. Yasin\n\
2025-06-29 08:18  PT-0002  appointment-view    Dr. Yasin\n\
2025-06-29 08:42  PT-0003  prescription-refill Dr. Brennan\n\
2025-06-29 09:01  PT-0004  appointment-view    Dr. Patel-Rao\n\
2025-06-29 09:15  PT-0005  lab-result-view     Dr. Wei\n\
2025-06-29 09:33  PT-0001  prescription-refill Dr. Yasin\n\
2025-06-29 10:02  PT-0006  appointment-view    Dr. Lassiter\n\
2025-06-29 10:11  PT-0007  imaging-order       Dr. Brennan\n\
\n\
End of sample.\n' > /srv/samba/phi-archive/access_log_sample.txt && \
    chown -R clinic_archivist:clinic_archivist /srv/samba/phi-archive && \
    chmod -R 770 /srv/samba/phi-archive

# Samba configuration
RUN printf '[global]\n\
   workgroup = PINECREST\n\
   server string = Pinecrest Family Practice File Server\n\
   security = user\n\
   map to guest = Bad User\n\
   log file = /var/log/samba/log.%%m\n\
   max log size = 50\n\
   server min protocol = NT1\n\
\n\
[clinic-shared]\n\
   path = /srv/samba/clinic-shared\n\
   browseable = yes\n\
   read only = yes\n\
   guest ok = yes\n\
   comment = Clinic shared documents\n\
\n\
[phi-archive]\n\
   path = /srv/samba/phi-archive\n\
   browseable = yes\n\
   read only = yes\n\
   guest ok = no\n\
   valid users = clinic_archivist\n\
   comment = Compliance archive\n' > /etc/samba/smb.conf

# SNMP configuration: recon flag in sysContact
RUN printf '# Pinecrest Family Practice File Server SNMP\n\
\n\
rocommunity public\n\
\n\
sysDescr    Pinecrest Family Practice File Server\n\
sysLocation Pinecrest Family Practice / Charlotte NC / Network Closet\n\
sysContact  Pinecrest IT (manager@pinecrestfp.com) | Equipment Token 1 = p1n3cr3st\n\
sysName     pinecrest-fs01\n\
\n\
agentAddress udp:161\n\
\n\
view all included .1\n\
rouser noAuthUser\n' > /etc/snmp/snmpd.conf

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 139 445 161/udp

CMD ["/start.sh"]
