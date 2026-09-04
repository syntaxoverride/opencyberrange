# Chapter 7: Review

## What You Learned

Over six labs, you learned to enumerate an LDAP directory from scratch. You started by detecting the service with Nmap, then tested whether the server accepts anonymous (unauthenticated) queries. You discovered the Base DN by querying the Root DSE, extracted every user account from the People OU, mapped security group memberships from the Groups OU, and finally combined all techniques into a single thorough enumeration pass. The usernames and group memberships you gathered form the foundation for credential attacks in the next chapter.

## The Progression You Followed

Each lab added one new layer to your LDAP enumeration capability:

```mermaid
graph LR
    A["7.1 Detect"] --> B["7.2 Anonymous Bind"]
    B --> C["7.3 Base DN"]
    C --> D["7.4 Users"]
    D --> E["7.5 Groups"]
    E --> F["7.6 Comprehensive"]

    style A fill:#4a90d9,color:#fff
    style F fill:#6aaa64,color:#fff
```

| Exercise | What You Added | Why It Matters |
|-----|---------------|----------------|
| 7.1 | LDAP service detection | Confirmed port 389 is open and identified the software as OpenLDAP slapd |
| 7.2 | Anonymous bind test | Proved the server accepts unauthenticated queries; a critical misconfiguration |
| 7.3 | Base DN discovery | Found the root of the directory tree, enabling all subsequent queries |
| 7.4 | User enumeration | Extracted every username, email, and user attribute from the directory |
| 7.5 | Group enumeration | Mapped security groups and identified Domain Admin members |
| 7.6 | Comprehensive enumeration | Combined all techniques into a repeatable methodology |

---

## Self-Assessment

Answer the following questions without looking back at the walkthroughs. If you get stuck on a question, that topic is worth revisiting before moving on.

**1.** What port does LDAP run on by default, and what port is used for LDAPS?

> &nbsp;
>
> &nbsp;

**2.** What ldapsearch command tests for anonymous bind access?

> &nbsp;
>
> &nbsp;

**3.** How do you query the Root DSE to discover the Base DN?

> &nbsp;
>
> &nbsp;

**4.** What does the `-x` flag do in ldapsearch?

> &nbsp;
>
> &nbsp;

**5.** What LDAP filter matches all user accounts of the inetOrgPerson class?

> &nbsp;
>
> &nbsp;

**6.** What is the difference between the `memberUid` and `member` group attributes?

> &nbsp;
>
> &nbsp;

**7.** Why is the Domain Admins group the highest-priority target during LDAP enumeration?

> &nbsp;
>
> &nbsp;

**8.** What Nmap script retrieves the Root DSE from an LDAP server?

> &nbsp;
>
> &nbsp;

---

## Command Cheat Sheet

Keep the following reference handy throughout the rest of the workbook.

| Command | What It Does |
|---------|-------------|
| `nmap -p 389 -sV <target>` | Detect LDAP service and version |
| `nmap -p 389 --script=ldap-rootdse <target>` | Extract Root DSE via Nmap |
| `nmap -p 389 --script=ldap-search <target>` | Automated LDAP search via Nmap |
| `ldapsearch -x -H ldap://<target> -b "" -s base "(objectclass=*)"` | Query the Root DSE for Base DN |
| `ldapsearch -x -H ldap://<target> -b "<base_dn>"` | Anonymous bind test / full dump |
| `ldapsearch -x -H ldap://<target> -b "<base_dn>" "(objectClass=organizationalUnit)"` | List all Organizational Units |
| `ldapsearch -x -H ldap://<target> -b "ou=Users,<base_dn>" "(objectClass=inetOrgPerson)"` | Enumerate all user accounts |
| `ldapsearch -x -H ldap://<target> -b "ou=Users,<base_dn>" "(objectClass=inetOrgPerson)" uid cn mail` | Users with specific attributes only |
| `ldapsearch -x -H ldap://<target> -b "ou=Groups,<base_dn>" "(objectClass=posixGroup)"` | Enumerate all POSIX groups |
| `ldapsearch -x -H ldap://<target> -b "ou=Groups,<base_dn>" "(objectClass=groupOfNames)"` | Enumerate groupOfNames groups |
| `ldapsearch -x -H ldap://<target> -b "<base_dn>" "(cn=Domain Admins)"` | Query a specific group by name |
| `ldapsearch -x -H ldap://<target> -b "<base_dn>" "(uid=jmitchell)"` | Query a specific user by uid |
| `ldapsearch -x -H ldap://<target> -b "<base_dn>" "(objectClass=*)" \| grep "OCR{"` | Full-subtree dump that reveals the flag in the service account |

---

## Key Concepts Reference

The following terms appeared throughout this chapter. Review any that you are not fully comfortable with.

| Term | Definition |
|------|-----------|
| LDAP | Lightweight Directory Access Protocol; a protocol for querying directory services |
| slapd | Stand-alone LDAP Daemon; the OpenLDAP server process |
| DN | Distinguished Name; the unique path identifying an entry in the directory tree |
| Base DN | The root entry of a directory partition (e.g., `dc=financecorp,dc=local`) |
| Root DSE | The top-level server metadata entry that advertises capabilities and naming contexts |
| Anonymous Bind | An LDAP connection made without any credentials |
| OU | Organizational Unit; a container that groups related directory entries |
| LDIF | LDAP Data Interchange Format; the standard text format for LDAP data |
| `dc` | Domain Component; a DN element representing part of the domain name |
| `cn` | Common Name; a DN element representing an object's name |
| `ou` | Organizational Unit; a DN element representing a container |
| `inetOrgPerson` | An object class for standard user accounts |
| `posixAccount` | An object class adding Unix-specific attributes to user entries |
| `posixGroup` | A group object class that stores members as simple usernames (memberUid) |
| `groupOfNames` | A group object class that stores members as full Distinguished Names |
| NSE | Nmap Scripting Engine; the framework for running scripts during Nmap scans |

---

## Connect the Dots: What Comes Next

You now have a complete picture of the FinanceCorp directory; every username, every email address, every group membership, and every privileged account. But directory data alone does not get you into the system. To move from enumeration to access, you need credentials.

Chapter 8 takes the usernames you extracted here and tests them against passwords. You will start with manual credential testing using known defaults, then progress to automated techniques like password spraying and brute force attacks. The Domain Admin accounts you identified in Exercise 7.5 become your primary targets. A single successful login against one of those accounts gives you full control over the domain.

The progression looks like the following: LDAP gave you the "who"; Chapter 8 finds the "how."

---

## Self-Assessment Answer Key

**1.** LDAP runs on port 389 (unencrypted). LDAPS runs on port 636 (encrypted with TLS).

**2.** `ldapsearch -x -H ldap://<target> -b "dc=financecorp,dc=local"`: the `-x` flag uses simple auth, and providing no `-D` or `-w` flags makes it an anonymous bind.

**3.** `ldapsearch -x -H ldap://<target> -b "" -s base "(objectclass=*)"`: the empty Base DN and base scope tell the server to return the Root DSE, which contains the `namingContexts` attribute.

**4.** The `-x` flag selects simple authentication instead of SASL. Simple auth is required for anonymous binds and plaintext credential binds. Without `-x`, ldapsearch defaults to SASL, which requires additional configuration.

**5.** `(objectClass=inetOrgPerson)`: an equality filter that matches any entry whose objectClass attribute includes inetOrgPerson.

**6.** The `memberUid` attribute (used by posixGroup) stores simple username strings like `jmitchell`. The `member` attribute (used by groupOfNames) stores full Distinguished Names like `uid=jmitchell,ou=Users,dc=financecorp,dc=local`. Different group object classes use different membership formats.

**7.** Domain Admins have unrestricted control over the entire domain. Compromising one Domain Admin account grants the ability to create accounts, modify access, extract credentials for all users, and access every resource. Identifying these accounts lets an attacker focus credential attacks on the highest-value targets.

**8.** The `ldap-rootdse` Nmap script queries the Root DSE and returns the server's namingContexts, supported LDAP versions, and other metadata. Run it with `nmap -p 389 --script=ldap-rootdse <target>`.
