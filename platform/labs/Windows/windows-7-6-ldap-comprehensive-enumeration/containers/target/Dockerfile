FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Preseed slapd for financecorp.local domain
RUN echo "slapd slapd/internal/adminpw password admin" | debconf-set-selections && \
    echo "slapd slapd/internal/generated_adminpw password admin" | debconf-set-selections && \
    echo "slapd slapd/password2 password admin" | debconf-set-selections && \
    echo "slapd slapd/password1 password admin" | debconf-set-selections && \
    echo "slapd slapd/domain string financecorp.local" | debconf-set-selections && \
    echo "slapd shared/organization string FinanceCorp" | debconf-set-selections && \
    echo "slapd slapd/backend string MDB" | debconf-set-selections && \
    echo "slapd slapd/purge_database boolean true" | debconf-set-selections && \
    echo "slapd slapd/move_old_database boolean true" | debconf-set-selections && \
    echo "slapd slapd/no_configuration boolean false" | debconf-set-selections

RUN apt-get update && apt-get install -y slapd ldap-utils && rm -rf /var/lib/apt/lists/*

# Load directory seed data (users, groups, OUs)
COPY seed.ldif /tmp/seed.ldif
RUN slapadd -F /etc/ldap/slapd.d -l /tmp/seed.ldif -b "dc=financecorp,dc=local" && \
    chown -R openldap:openldap /var/lib/ldap /etc/ldap/slapd.d

EXPOSE 389
CMD ["slapd", "-d", "0", "-h", "ldap:///"]
