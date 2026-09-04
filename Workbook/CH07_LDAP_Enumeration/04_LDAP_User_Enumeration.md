# Exercise 7.4: LDAP User Enumeration

## Before You Begin

In Exercise 7.3 you discovered the Base DN and saw the organizational structure of the FinanceCorp directory. You know that user accounts live under `ou=Users,dc=financecorp,dc=local`. Now you will query that container directly and extract every user account along with their attributes; names, email addresses, user IDs, and home directories.

## Scenario

You are moving deeper into the FinanceCorp LDAP assessment. The engagement lead wants a complete list of user accounts from the directory. Usernames are the most valuable output of LDAP enumeration because they feed directly into credential attacks. Every username you extract is one you can later test against password policies, spray with common passwords, or use in targeted phishing. Your task is to enumerate all users and document their attributes.

## Your Objectives

- Query the LDAP directory for all user account entries
- Use LDAP search filters to target specific object classes
- Extract key user attributes: uid, cn, sn, mail, uidNumber, homeDirectory
- Understand how LDAP search filters work
- Capture the flag embedded in the directory data

---

## Background: LDAP Search Filters and User Objects

LDAP search filters control which entries the server returns. A filter is a string enclosed in parentheses that specifies conditions an entry must meet. Every LDAP query includes a filter, even if it is just the wildcard `(objectclass=*)` that matches everything.

Filters follow a prefix notation syntax. The operator comes first, followed by the attribute name and value. Here are the filter types you need to understand:

| Filter Type | Syntax | Example | Meaning |
|------------|--------|---------|---------|
| Equality | `(attribute=value)` | `(uid=jmitchell)` | uid equals "jmitchell" |
| Presence | `(attribute=*)` | `(mail=*)` | Entry has a mail attribute |
| Wildcard | `(attribute=val*)` | `(cn=J*)` | cn starts with "J" |
| AND | `(&(filter1)(filter2))` | `(&(objectClass=inetOrgPerson)(uid=jmitchell))` | Both conditions must be true |
| OR | `(|(filter1)(filter2))` | `(|(uid=jmitchell)(uid=schen))` | Either condition can be true |
| NOT | `(!(filter))` | `(!(uid=svc-backup))` | uid is not "svc-backup" |

User accounts in OpenLDAP directories typically use one of two object classes. The `inetOrgPerson` class represents standard organizational users and includes attributes like `uid`, `cn` (common name), `sn` (surname), `mail`, and `telephoneNumber`. The `posixAccount` class adds Unix-specific attributes like `uidNumber`, `gidNumber`, `homeDirectory`, and `loginShell`. Many entries use both classes simultaneously.

The attributes stored on each user entry paint a detailed picture of the person and their role. Here is what the key attributes tell you:

| Attribute | Meaning | Attacker Value |
|-----------|---------|---------------|
| `uid` | Username / login ID | Primary target for credential attacks |
| `cn` | Full name (Common Name) | Useful for social engineering and phishing |
| `sn` | Last name (Surname) | Helps identify individuals |
| `mail` | Email address | Phishing target, may also be a login ID |
| `uidNumber` | Numeric Unix user ID | Identifies privileged accounts (low UIDs) |
| `gidNumber` | Primary group ID number | Reveals group membership |
| `homeDirectory` | User's home directory path | Reveals naming conventions and system paths |

---

## Tool Primer: ldapsearch with Filters and Attribute Selection

You already know the basic ldapsearch syntax from Exercise 7.2. In this exercise you will add two new capabilities: search filters and attribute selection.

!!! kali "User enumeration syntax"
    Replace `<target_ip>` with the target IP from the Active Lab View. The first command lists every user account in the Users OU.

    ```bash
    ldapsearch -x -H ldap://<target_ip> \
      -b "ou=Users,dc=financecorp,dc=local" \
      "(objectClass=inetOrgPerson)"
    ```

    To cut the output down to only the fields you care about, append an attribute list. The next command returns just the uid, cn, and mail attributes.

    ```bash
    ldapsearch -x -H ldap://<target_ip> \
      -b "ou=Users,dc=financecorp,dc=local" \
      "(objectClass=inetOrgPerson)" \
      uid cn mail
    ```

    The new elements in these commands serve specific purposes:

    | Element | Purpose |
    |---------|---------|
    | `-b "ou=Users,dc=financecorp,dc=local"` | Narrow the search to only the Users OU instead of the entire directory |
    | `"(objectClass=inetOrgPerson)"` | Filter; only return entries that are user accounts |
    | `uid cn mail` | Attribute list; only return these specific attributes instead of all attributes |

**Sample output:**

```
# jmitchell, Users, financecorp.local
dn: uid=jmitchell,ou=Users,dc=financecorp,dc=local
objectClass: inetOrgPerson
objectClass: posixAccount
uid: jmitchell
cn: James Mitchell
sn: Mitchell
mail: jmitchell@financecorp.local
uidNumber: 1001
gidNumber: 1000
homeDirectory: /home/jmitchell
```

Each entry block begins with a comment line showing the entry's location, followed by the DN and then all matching attributes.

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** then **Windows** then **Level 1**
- Click **Launch** on "LDAP User Enumeration"
- Wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Enumerate All Users

!!! kali "Enumerate all users"
    Run an ldapsearch query targeting user accounts in the Users OU:

    ```bash
    ldapsearch -x -H ldap://<target_ip> \
      -b "ou=Users,dc=financecorp,dc=local" \
      "(objectClass=inetOrgPerson)"
    ```

    The filter `(objectClass=inetOrgPerson)` matches standard user account entries. The Base DN is set to `ou=Users` to search only the container where users are stored. Examine the output and note how many user entries are returned.

### Step 3: Extract Specific Attributes

!!! kali "Extract specific attributes"
    The full output includes every attribute on each user entry, which can be overwhelming. Narrow the results to just the attributes that matter for penetration testing:

    ```bash
    ldapsearch -x -H ldap://<target_ip> \
      -b "ou=Users,dc=financecorp,dc=local" \
      "(objectClass=inetOrgPerson)" \
      uid cn mail
    ```

    Adding `uid cn mail` at the end of the command tells ldapsearch to return only those three attributes. The output becomes much cleaner and easier to parse.

### Step 4: Try an Alternative Filter

!!! kali "Try an alternative filter"
    Some LDAP directories use `posixAccount` instead of `inetOrgPerson` for their user entries. Run the same query with a different filter to see if additional accounts appear:

    ```bash
    ldapsearch -x -H ldap://<target_ip> \
      -b "ou=Users,dc=financecorp,dc=local" \
      "(objectClass=posixAccount)" uid cn
    ```

    Compare the results from both queries. In the FinanceCorp lab, the same users should appear because each entry uses both object classes.

### Step 5: Search for a Specific User

!!! kali "Search for a specific user"
    Demonstrate targeted enumeration by searching for a single user by uid:

    ```bash
    ldapsearch -x -H ldap://<target_ip> \
      -b "ou=Users,dc=financecorp,dc=local" \
      "(uid=jmitchell)"
    ```

    The equality filter `(uid=jmitchell)` returns only the entry where the uid attribute matches "jmitchell". Replace `jmitchell` with any username you found in Step 2 to pull their full record.

### Step 6: Build a Username List

!!! kali "Build a username list"
    Combine ldapsearch with a targeted attribute request to produce a clean list of usernames:

    ```bash
    ldapsearch -x -H ldap://<target_ip> \
      -b "ou=Users,dc=financecorp,dc=local" \
      "(objectClass=inetOrgPerson)" uid | grep "^uid:"
    ```

    The `grep "^uid:"` filters the output to show only lines that begin with `uid:`, giving you a clean list of every username in the directory. In a real engagement, you would save this list to a file for use in credential attacks.

### Step 7: Find the Flag in the Service Accounts OU

!!! kali "Search the whole directory for the flag"
    The Users OU holds the standard staff accounts, but FinanceCorp stores its service accounts in a separate OU named `ou=ServiceAccounts`. The flag rides in the `description` attribute of the `svc-backup` service account, so a search scoped to `ou=Users` will not reach it. Run a full-subtree search from the Base DN and read every entry:

    ```bash
    ldapsearch -x -H ldap://<target_ip> \
      -b "dc=financecorp,dc=local" \
      "(objectClass=*)"
    ```

    To jump straight to the flag, pipe the output through grep:

    ```bash
    ldapsearch -x -H ldap://<target_ip> \
      -b "dc=financecorp,dc=local" \
      "(objectClass=*)" | grep "OCR{"
    ```

    The flag appears on the `uid=svc-backup,ou=ServiceAccounts,dc=financecorp,dc=local` entry in `OCR{...}` format.

---

### Record Your Findings

> **Total number of user accounts found:** ___________________________
>
> **User account summary:**
>
> | uid | cn (Full Name) | mail |
> |-----|---------------|------|
> |     |               |      |
> |     |               |      |
> |     |               |      |
> |     |               |      |
> |     |               |      |
>
> **Any accounts with low uidNumbers (potential privileged accounts)?** ___________________________
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** ___________________________

---

### Step 8: Record the Flag

The flag appears within the service account entry in `OCR{<flag_here>}` format. Copy it and paste it into the **Submit Flag** form on the platform and click **Submit**.

---

## Analysis Questions

**1. Why is user enumeration considered the most valuable LDAP finding?**

??? note "Reveal Answer"

    Usernames are the first half of the credential puzzle. With a complete list of valid usernames, an attacker can perform password spraying (trying one common password against every account), targeted brute force attacks, or credential stuffing using passwords from breached databases. Without valid usernames, an attacker has to guess both the username and password; which is exponentially harder.

**2. What is the difference between querying with `(objectClass=inetOrgPerson)` versus `(objectClass=posixAccount)`?**

??? note "Reveal Answer"

    The `inetOrgPerson` class is a general-purpose user object class defined in RFC 2798 that includes attributes like uid, cn, sn, and mail. The `posixAccount` class adds Unix/Linux-specific attributes such as uidNumber, gidNumber, homeDirectory, and loginShell. Many LDAP entries belong to both classes simultaneously. Querying with either filter may return the same users, but the attributes available will differ based on which classes the entry belongs to.

**3. How could an attacker use the homeDirectory attribute in later attack stages?**

??? note "Reveal Answer"

    The homeDirectory attribute reveals the file system path structure on the server (e.g., `/home/jmitchell`). Knowing the naming convention helps an attacker predict paths for other users, locate potential SSH key files (`/home/jmitchell/.ssh/`), identify network-mounted home directories, and understand the server's operating system and directory layout. Path patterns can also reveal whether user accounts are local or centrally managed.

**4. You used `grep` to extract a clean username list. Why is generating a username list file important?**

??? note "Reveal Answer"

    A clean username list feeds directly into automated tools. Password spraying tools like Hydra, Medusa, and CrackMapExec accept username list files as input. Having a validated list of real usernames eliminates guesswork and makes credential attacks far more efficient. The list is also valuable for email-based attacks, social engineering, and mapping the organizational hierarchy.

---

## Key Takeaways

- LDAP search filters like `(objectClass=inetOrgPerson)` let you target specific types of directory entries
- User accounts contain valuable attributes: uid, cn, sn, mail, uidNumber, homeDirectory
- Narrowing the Base DN to `ou=Users` focuses the search on user accounts only, but a scoped search will miss entries stored in other OUs such as `ou=ServiceAccounts`
- Appending attribute names to the ldapsearch command limits which fields are returned
- A clean username list extracted from LDAP is the foundation for credential attacks in later chapters
- Now that you have user accounts, the next exercise enumerates security groups to understand who has privileged access
