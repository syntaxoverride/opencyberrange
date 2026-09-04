#!/bin/bash

# Import LDAP directory entries after slapd starts
(
  sleep 3
  ldapadd -x -D "cn=admin,dc=pinnacle,dc=legal" -w admin -f /entries.ldif 2>/dev/null || true
) &

# Start Samba (daemon mode)
smbd -D

# Start xrdp
xrdp

# Kerberos port placeholder (appears open for enumeration)
socat TCP-LISTEN:88,fork,reuseaddr EXEC:/bin/true &

# Start slapd in foreground (keeps container alive)
exec slapd -h "ldap:///" -g openldap -u openldap -d 0
