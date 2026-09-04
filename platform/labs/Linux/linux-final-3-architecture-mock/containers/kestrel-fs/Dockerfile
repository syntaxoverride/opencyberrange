FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba \
    snmpd \
    snmp \
    && rm -rf /var/lib/apt/lists/*

# Samba user for the locked project-archive share
RUN useradd -M -s /usr/sbin/nologin studio_archivist && \
    printf 'Arch_K3str3l_2024#\nArch_K3str3l_2024#\n' | smbpasswd -a -s studio_archivist

# Public share: studio-shared
RUN mkdir -p /srv/samba/studio-shared && \
    printf 'KESTREL ARCHITECTURE STUDIO\n\
INTERNAL FILE SERVER\n\
=============================\n\
\n\
Shared studio documents. Active project files live in Newforma;\n\
this server holds reference materials, vendor lists, and the\n\
closed-project archive.\n\
\n\
For studio support, contact the managing partner.\n\
- Kestrel Architecture Studio\n' > /srv/samba/studio-shared/README.txt && \
    printf 'KESTREL STUDIO. STAFF DIRECTORY\n\
================================\n\
\n\
Margo Whittaker         Managing Partner       ext. 100\n\
Daniel Okonkwo          Senior Architect       ext. 101\n\
Priya Ramaswamy         Senior Architect       ext. 102\n\
Theo Lindqvist          Architect              ext. 103\n\
Hana Sato               Architect              ext. 104\n\
Jules Bertrand          Project Architect      ext. 105\n\
Grace Halloran          Designer               ext. 106\n\
Aiden Wexler            Designer               ext. 107\n\
Mira Castellanos        Designer               ext. 108\n\
Quinn Faraday           Designer               ext. 109\n\
Robin DeWitt            Office Coordinator     ext. 200\n\
Sam Vellanki            Bookkeeper             ext. 201\n\
\n\
Last updated: 2025-08-22\n' > /srv/samba/studio-shared/staff_directory.txt && \
    printf 'CAD STANDARDS REFERENCE\n\
========================\n\
\n\
Layer naming follows AIA CAD Layer Guidelines (2nd Ed.).\n\
Title block template: KESTREL_TB_v3.dwg (in Newforma).\n\
Sheet sizes: ARCH D (24x36) for construction docs, ARCH B\n\
(11x17) for client review sets.\n\
\n\
Plot styles live in the Newforma project workspace.\n' > /srv/samba/studio-shared/cad_standards.txt && \
    printf 'PREFERRED VENDORS. KESTREL STUDIO\n\
===================================\n\
\n\
Structural        Eberhardt Engineering            (503) 555-0177\n\
MEP               Pacific Crest MEP Consultants    (503) 555-0188\n\
Civil             Bridgewater Civil Group          (503) 555-0144\n\
Renderings        Slate Visualizations             (503) 555-0123\n\
Reprographics     Northwest Print and Plot         (503) 555-0166\n\
Permit Expediting Whitcomb Permitting Services     (503) 555-0145\n\
\n\
Updated: 2025-09-04\n' > /srv/samba/studio-shared/preferred_vendors.txt && \
    printf 'IT INVENTORY. KESTREL STUDIO\n\
==============================\n\
Author: Bryce Halloran, Studio IT Generalist\n\
Last entry: 2025-02-28 (final week before departure)\n\
\n\
Leaving notes for whoever picks this up. The studio is moving\n\
most everything to managed cloud services so this list is the\n\
bare minimum for the on-prem footprint that will remain.\n\
\n\
=== File server (this host, kestrel-fs01) ===\n\
- Two Samba shares: studio-shared (open to studio staff) and\n\
  project-archive (locked to studio_archivist).\n\
- The project-archive share holds the index and closeout\n\
  packages for projects that have been delivered. Restricted\n\
  because some closeout packages contain client billing data.\n\
- studio_archivist credentials: password is Arch_K3str3l_2024#\n\
  This is a service account I set up; rotate after handoff.\n\
\n\
=== Project CMS (kestrel-cms) ===\n\
- Old internal project tracking tool I built for the studio.\n\
- Login is at /staff/ on port 80. The path is hidden from\n\
  the navigation and from search engines via robots.txt.\n\
- The application stores project metadata only, no drawings.\n\
- Margo asked about decommissioning it after the Newforma cut\n\
  over. It is still up because we never actually pulled the\n\
  plug.\n\
\n\
=== Network ===\n\
- SNMP is enabled on this file server with the public community\n\
  string. The asset tag for the equipment lease is set in the\n\
  sysContact field so the vendor can pull it on audit.\n\
\n\
=== Outstanding items ===\n\
- Decommission Project CMS.\n\
- Rotate studio_archivist credentials.\n\
- Audit who still has Newforma access from the prior contractor.\n\
\n\
- Bryce\n' > /srv/samba/studio-shared/IT_Inventory_2025.txt && \
    chmod -R 755 /srv/samba/studio-shared

# Restricted share: project-archive (requires studio_archivist credentials)
RUN mkdir -p /srv/samba/project-archive && \
    printf 'CLOSED PROJECT INDEX. KESTREL STUDIO\n\
======================================\n\
Last reconciled: 2025-09-30\n\
Engagement token (2 of 3): token=bluepr1nt\n\
\n\
This index lists projects whose closeout packages have been\n\
filed in the project-archive share. Project numbers follow\n\
the YY-NNN convention (year of contract execution).\n\
\n\
24-001  Cedar Mill Residence            Residential SFR\n\
24-007  Hawthorne Studios Lobby Refresh Commercial TI\n\
24-014  Sellwood Bridge Cafe Buildout   Commercial TI\n\
24-022  Beaverton Mews Townhomes        Residential MFR\n\
24-031  Forest Park Trail Pavilion      Civic Small\n\
25-002  Northwest Library Expansion     Civic Mid\n\
25-009  Albina Mixed Use Phase I        Mixed Use\n\
25-015  Tabor Heights Custom Residence  Residential SFR\n\
25-019  Riverplace Marina Office        Commercial New\n\
25-024  Holladay Park Daycare           Civic Small\n\
\n\
Each project folder contains: contract, schematic design set,\n\
design development set, construction documents (signed and\n\
sealed), permit submittals, and closeout (record drawings,\n\
specs, vendor warranties).\n\
\n\
Index maintained by the studio archivist account.\n' > /srv/samba/project-archive/closed_projects_index.txt && \
    printf 'PROJECT 25-019 RIVERPLACE MARINA OFFICE\n\
CLOSEOUT RECORD SUMMARY\n\
=========================================\n\
\n\
Contract executed:      2025-03-14\n\
Substantial completion: 2025-09-08\n\
Final billing posted:   2025-09-22\n\
\n\
Sheet count:            38 sheets at ARCH D\n\
Specifications:         CSI MasterFormat, divisions 01 through 33\n\
Permit number:          PDX-2025-CMRC-04417\n\
\n\
Consultants of record\n\
  Structural          Eberhardt Engineering\n\
  MEP                 Pacific Crest MEP Consultants\n\
  Civil               Bridgewater Civil Group\n\
\n\
Closeout package was uploaded to the archive on 2025-09-30.\n\
Record drawings reviewed and stamped by Daniel Okonkwo, AIA.\n' > /srv/samba/project-archive/25-019_closeout_summary.txt && \
    chown -R studio_archivist:studio_archivist /srv/samba/project-archive && \
    chmod -R 770 /srv/samba/project-archive

# Samba configuration
RUN printf '[global]\n\
   workgroup = KESTREL\n\
   server string = Kestrel Architecture Studio File Server\n\
   security = user\n\
   map to guest = Bad User\n\
   log file = /var/log/samba/log.%%m\n\
   max log size = 50\n\
   server min protocol = NT1\n\
\n\
[studio-shared]\n\
   path = /srv/samba/studio-shared\n\
   browseable = yes\n\
   read only = yes\n\
   guest ok = yes\n\
   comment = Studio shared documents\n\
\n\
[project-archive]\n\
   path = /srv/samba/project-archive\n\
   browseable = yes\n\
   read only = yes\n\
   guest ok = no\n\
   valid users = studio_archivist\n\
   comment = Closed project archive\n' > /etc/samba/smb.conf

# SNMP configuration: recon flag in sysContact
RUN printf '# Kestrel Architecture Studio File Server SNMP\n\
\n\
rocommunity public\n\
\n\
sysDescr    Kestrel Architecture Studio File Server\n\
sysLocation Kestrel Studio / Portland OR / Studio Closet\n\
sysContact  Kestrel IT (it@kestrelstudio.example) | Engagement token (3 of 3): token=t4lon\n\
sysName     kestrel-fs01\n\
\n\
agentAddress udp:161\n\
\n\
view all included .1\n\
rouser noAuthUser\n' > /etc/snmp/snmpd.conf

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 139 445 161/udp

CMD ["/start.sh"]
