FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Pre-seed slapd configuration for domain pinnacle.legal
RUN echo "slapd slapd/internal/generated_adminpw password admin" | debconf-set-selections && \
    echo "slapd slapd/internal/adminpw password admin" | debconf-set-selections && \
    echo "slapd slapd/password1 password admin" | debconf-set-selections && \
    echo "slapd slapd/password2 password admin" | debconf-set-selections && \
    echo "slapd slapd/domain string pinnacle.legal" | debconf-set-selections && \
    echo "slapd slapd/backend string MDB" | debconf-set-selections && \
    echo "slapd slapd/purge_database boolean true" | debconf-set-selections && \
    echo "slapd slapd/move_old_database boolean true" | debconf-set-selections && \
    echo "slapd slapd/no_configuration boolean false" | debconf-set-selections

RUN apt-get update && apt-get install -y --no-install-recommends \
    slapd ldap-utils samba xrdp socat \
    && dpkg-reconfigure -f noninteractive slapd \
    && rm -rf /var/lib/apt/lists/*

# Configure Samba with authenticated share for case records
RUN printf '[global]\n\
workgroup = PINNACLE\n\
server string = Pinnacle Legal Case Management Server\n\
netbios name = PLG-CASE01\n\
security = user\n\
map to guest = Bad User\n\
log level = 0\n\
log file = /dev/null\n\
\n\
[records]\n\
path = /srv/shares/records\n\
valid users = attorney\n\
read only = yes\n\
browsable = yes\n\
comment = Case Records\n' > /etc/samba/smb.conf

# Create attorney user and SMB password
RUN useradd -m -s /bin/bash attorney && \
    echo 'attorney:CaseFile2024#' | chpasswd && \
    (echo 'CaseFile2024#'; echo 'CaseFile2024#') | smbpasswd -a -s attorney

# Create share directory and flag
RUN mkdir -p /srv/shares/records && \
    echo "Flag 3: 3xp0s3d" > /srv/shares/records/flag-part.txt && \
    printf 'case_id,case_name,status,lead_attorney\nPLG-2025-001,Meridian Corp v. TechStart,Active,m.thompson\nPLG-2025-002,Greenfield IP Dispute,Settled,d.chen\nPLG-2025-003,Atlas Manufacturing Breach,Discovery,j.ramirez\nPLG-2025-004,Summit Realty Zoning Appeal,Pending,r.kessler\n' > /srv/shares/records/case-index.csv && \
    chmod 755 /srv/shares/records && chmod 644 /srv/shares/records/*

# Copy LDAP entries and startup script
COPY entries.ldif /entries.ldif
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 88 389 445 3389

CMD ["/start.sh"]
