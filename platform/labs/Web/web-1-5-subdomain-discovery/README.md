# Lab 1.5: Subdomain Discovery (Simulated)

## ⚠️ Important Lab Environment Notes

**This lab simulates subdomain discovery without actual DNS infrastructure.**

### Critical Limitations:

1. **No DNS Server**: This lab environment does NOT have a functioning DNS server. DNS-based enumeration tools (dnsrecon, gobuster dns, etc.) will NOT work.

2. **Manual /etc/hosts Required**: All subdomains must be manually added to `/etc/hosts` before they can be accessed by hostname. This is NOT how subdomain discovery works in real environments.

3. **IP-Based Discovery**: The actual discovery method in this lab is testing IP addresses directly, then manually mapping them to hostnames in `/etc/hosts`.

4. **This is a Simulation**: This lab teaches the CONCEPT of subdomain discovery, but uses a simulated approach suitable for a lab environment without DNS infrastructure.

---

## Learning Objectives

- Understand subdomain enumeration concepts
- Learn how subdomain discovery works in real-world environments
- Practice simulated subdomain discovery using HTTP-based techniques
- Perform IP-based enumeration and manual hostname mapping
- Identify subdomains through HTTP response testing
- Capture the flag

---

## Part 1: Real-World Subdomain Discovery Concepts

### What is Subdomain Discovery?

Subdomain discovery is the process of finding subdomains associated with a domain. In real-world environments, this typically involves:

- **DNS Enumeration**: Querying DNS servers to discover subdomain records
- **Certificate Transparency Logs**: Searching public certificate databases
- **Search Engines**: Using Google dorks and specialized search tools
- **Brute Forcing**: Testing common subdomain names against DNS servers
- **Passive DNS**: Analyzing historical DNS data

### Why Subdomain Discovery Matters

Subdomains often:
- Host different applications or services
- Have different security configurations
- Contain sensitive information
- Provide additional attack surface
- May be forgotten or less secure than main domain

### Common Subdomains

- `admin.example.com` - Admin panels
- `api.example.com` - API endpoints
- `dev.example.com` - Development environments
- `test.example.com` - Testing environments
- `staging.example.com` - Staging environments
- `www.example.com` - World Wide Web (main site)
- `mail.example.com` - Email servers
- `ftp.example.com` - File transfer servers

### Real-World Tools (For Reference Only)

In real environments, these tools query DNS servers:

- **dnsrecon**: DNS enumeration tool that queries DNS servers
- **gobuster dns**: DNS brute-forcing tool
- **sublist3r**: Passive subdomain enumeration using search engines
- **amass**: Comprehensive subdomain enumeration tool
- **ffuf**: HTTP-based subdomain brute-forcing (works without DNS)

**Note**: In this lab, DNS-based tools will NOT work because there is no DNS server. We will use HTTP-based methods instead.

---

## Part 2: Lab Environment - Simulated Subdomain Discovery

### How This Lab Works

Since this lab environment has no DNS infrastructure, we simulate subdomain discovery using:

1. **IP Address Testing**: Test potential IP addresses to find active services
2. **HTTP Response Analysis**: Check HTTP responses to identify subdomains
3. **Manual Hostname Mapping**: Map discovered IPs to hostnames in `/etc/hosts`

### ⚠️ Important: /etc/hosts Requirement

**All subdomains MUST be added to `/etc/hosts` before they can be accessed by hostname.**

This is NOT how real subdomain discovery works, but it's necessary in this lab environment.

---

## Solution Walkthrough

### Step 1: Add Main Hostname to /etc/hosts

First, add the main domain to your `/etc/hosts` file:

```bash
# Determine your target IP from the lab platform
# Example: If your target IP is 10.X.Y.127, main.lab would be at that IP
# Replace with your actual IP
sudo bash -c 'echo "<target_ip>    main.lab" >> /etc/hosts'

# Verify it was added
cat /etc/hosts | grep lab
```

### Step 2: Initial Reconnaissance

Test that the main domain is accessible:

```bash
curl http://main.lab
# Or test by IP directly
curl http://<target_ip>
```

### Step 3: IP-Based Subdomain Discovery

Since DNS enumeration won't work, we'll discover subdomains by testing IP addresses directly.

**Method: Test IP Addresses, Then Map to Hostnames**

1. **Create a subdomain wordlist:**
   ```bash
   echo -e "admin\napi\ndev\ntest\nstaging\nwww\nmail\nftp" > subdomains.txt
   cat subdomains.txt
   ```

2. **Determine your base IP:**
   ```bash
   # If your target IP is at 10.X.Y.127, your base subnet is 10.X.Y
   # Subdomains typically use offsets: +4, +10, +14, etc.
   BASE_IP="10.X.Y"  # Replace with your actual base subnet from the lab panel
   ```

3. **Test potential IP addresses:**
   ```bash
   # Test common IP offsets for subdomains
   for offset in 127 131 137 141 145; do
       ip="${BASE_IP}.${offset}"
       echo "Testing $ip..."
       status_code=$(curl -s -o /dev/null -w "%{http_code}" http://$ip)
       if [ "$status_code" = "200" ] || [ "$status_code" = "301" ] || [ "$status_code" = "302" ]; then
           echo "[+] Found active service at $ip - HTTP $status_code"
       fi
   done
   ```

   **Expected output:**
   ```
   Testing <base_subnet>.127...
   [+] Found active service at <base_subnet>.127 - HTTP 200
   Testing <base_subnet>.131...
   [+] Found active service at <base_subnet>.131 - HTTP 200
   Testing <base_subnet>.137...
   [+] Found active service at <base_subnet>.137 - HTTP 200
   Testing <base_subnet>.141...
   Testing <base_subnet>.145...
   ```

4. **Map discovered IPs to hostnames in /etc/hosts:**
   ```bash
   # Based on your testing, add subdomains to /etc/hosts
   # Common mappings: offset 131 = admin, offset 137 = api
   sudo bash -c 'echo "<discovered_ip>    admin.lab" >> /etc/hosts'
   sudo bash -c 'echo "<discovered_ip>    api.lab" >> /etc/hosts'
   
   # Verify entries
   cat /etc/hosts | grep lab
   ```

5. **Test subdomains by hostname:**
   ```bash
   for subdomain in $(cat subdomains.txt); do
       echo "Testing $subdomain.lab..."
       status_code=$(curl -s -o /dev/null -w "%{http_code}" http://$subdomain.lab 2>/dev/null)
       if [ "$status_code" = "200" ] || [ "$status_code" = "301" ] || [ "$status_code" = "302" ]; then
           echo "[+] Found: $subdomain.lab - HTTP $status_code"
       elif [ -n "$status_code" ] && [ "$status_code" != "000" ]; then
           echo "[-] $subdomain.lab - HTTP $status_code"
       else
           echo "[-] $subdomain.lab - Not in /etc/hosts or wrong IP"
       fi
   done
   ```

   **Expected output:**
   ```
   Testing admin.lab...
   [+] Found: admin.lab - HTTP 200
   Testing api.lab...
   [+] Found: api.lab - HTTP 200
   Testing dev.lab...
   [-] dev.lab - Not in /etc/hosts or wrong IP
   Testing test.lab...
   [-] test.lab - Not in /etc/hosts or wrong IP
   ...
   ```

### Step 4: HTTP-Based Subdomain Brute Forcing (Alternative Method)

You can also use HTTP-based tools that work without DNS:

**Using FFUF (HTTP-based, works without DNS):**

```bash
# FFUF tests HTTP responses directly, doesn't need DNS
ffuf -w subdomains.txt -u http://FUZZ.lab -mc 200,301,302 -t 20

# Note: This still requires subdomains to be in /etc/hosts first
# But it's more efficient than manual testing
```

**Using a Custom Script:**

```bash
#!/bin/bash
DOMAIN="lab"
WORDLIST="subdomains.txt"

while read subdomain; do
    echo "Testing $subdomain.$DOMAIN..."
    status_code=$(curl -s -o /dev/null -w "%{http_code}" http://$subdomain.$DOMAIN 2>/dev/null)
    if [ "$status_code" = "200" ] || [ "$status_code" = "301" ] || [ "$status_code" = "302" ]; then
        echo "[+] Found: $subdomain.$DOMAIN - HTTP $status_code"
    fi
done < $WORDLIST
```

### Step 5: Access Admin Subdomain and Retrieve Flag

Once you've discovered the admin subdomain:

1. **Verify admin subdomain is accessible:**
   ```bash
   curl -I http://admin.lab
   ```

   **Expected output:**
   ```
   HTTP/1.1 200 OK
   Server: Apache/2.4.52
   Content-Type: text/html
   ```

2. **Get the main page:**
   ```bash
   curl http://admin.lab
   ```

3. **Retrieve the flag:**
   ```bash
   curl http://admin.lab/flag.txt
   ```

   **Expected output:**
   ```
   OCR{subd0m41n_d1sc0v3ry_b4s1c}
   ```

4. **Alternative flag locations (if needed):**
   ```bash
   curl http://admin.lab/flag
   curl http://admin.lab/FLAG.txt
   curl http://admin.lab/.flag.txt
   ```

**Flag:**
```
OCR{subd0m41n_d1sc0v3ry_b4s1c}
```

---

## Demonstration: DNS Tools (Expected to Fail)

The following commands demonstrate DNS-based enumeration tools, but **they will NOT work in this lab environment** because there is no DNS server.

### Why These Commands Fail

- **No DNS Server**: The lab environment has no DNS infrastructure
- **No DNS Resolution**: Tools cannot query DNS records
- **Expected Behavior**: These commands will fail or return no results

### dnsrecon (Demonstration Only)

```bash
# This command will NOT work in this lab
# It requires a DNS server, which this lab does not have
dnsrecon -d lab -D /usr/share/wordlists/dnsmap.txt -t brt
```

**Expected result**: Command fails or returns no results (this is normal)

### Gobuster DNS (Demonstration Only)

```bash
# This command will NOT work in this lab
# Newer versions of gobuster use --domain instead of -d
gobuster dns --domain lab -w /usr/share/wordlists/dnsmap.txt
```

**Expected result**: Command fails or returns no results (this is normal)

**Note**: In real environments with DNS servers, these tools would work. In this lab, we use HTTP-based methods instead.

---

## Alternative HTTP-Based Tools (These Work)

These tools test HTTP responses directly and work without DNS:

### FFUF

```bash
# HTTP-based subdomain brute-forcing (works without DNS)
# Note: Subdomains must be in /etc/hosts first
ffuf -w subdomains.txt -u http://FUZZ.lab -mc 200,301,302 -t 20

# With custom wordlist
ffuf -w /usr/share/wordlists/dnsmap.txt -u http://FUZZ.lab -mc 200 -t 20
```

### Custom Bash Script

```bash
#!/bin/bash
DOMAIN="lab"
WORDLIST="subdomains.txt"

while read subdomain; do
    echo "Testing $subdomain.$DOMAIN..."
    status_code=$(curl -s -o /dev/null -w "%{http_code}" http://$subdomain.$DOMAIN 2>/dev/null)
    if [ "$status_code" = "200" ] || [ "$status_code" = "301" ] || [ "$status_code" = "302" ]; then
        echo "[+] Found: $subdomain.$DOMAIN - HTTP $status_code"
    fi
done < $WORDLIST
```

---

## Troubleshooting

### "Could not resolve host" Error

**Cause**: Subdomain is not in `/etc/hosts` or has wrong IP

**Solution**:
```bash
# Add subdomain to /etc/hosts
sudo bash -c 'echo "<discovered_ip>    api.lab" >> /etc/hosts'

# Verify entry
cat /etc/hosts | grep api.lab

# Test again
curl -I http://api.lab
```

### All Subdomains Return 404

**Cause**: IP addresses in `/etc/hosts` are incorrect

**Solution**:
```bash
# Test IP directly first
curl -I http://<discovered_ip>

# If IP works, verify /etc/hosts entry matches
cat /etc/hosts | grep <discovered_ip>
```

### DNS Tools Not Working

**This is expected!** DNS-based tools (dnsrecon, gobuster dns) will NOT work in this lab because there is no DNS server. Use HTTP-based methods instead.

---

## Success Criteria

- ✅ Successfully added main hostname to /etc/hosts
- ✅ Performed IP-based discovery to find active services
- ✅ Mapped discovered IPs to hostnames in /etc/hosts
- ✅ Successfully tested subdomains by hostname
- ✅ Discovered admin and api subdomains
- ✅ Successfully accessed admin subdomain
- ✅ Retrieved flag from admin subdomain
- ✅ Verified flag format is correct: `OCR{...}`

---

## Key Takeaways

### Real-World vs. Lab Environment

| Real-World | Lab Environment |
|------------|----------------|
| DNS servers available | No DNS infrastructure |
| DNS-based tools work | DNS-based tools fail |
| Automatic hostname resolution | Manual /etc/hosts required |
| Query DNS records | Test IP addresses directly |

### What You Learned

1. **Concepts**: How subdomain discovery works in real environments
2. **Simulation**: How to simulate subdomain discovery without DNS
3. **HTTP-Based Enumeration**: Testing IPs and HTTP responses
4. **Manual Mapping**: Mapping IPs to hostnames in /etc/hosts

---

## Further Reading

- OWASP: Testing for Subdomain Takeover
- DNS Enumeration Techniques (for real-world environments)
- Certificate Transparency Logs
- HTTP-Based Subdomain Discovery

---

## Common Mistakes

- ❌ Trying to use DNS tools without understanding they won't work
- ❌ Not adding subdomains to /etc/hosts before testing
- ❌ Assuming DNS enumeration will work in lab environment
- ❌ Not testing IP addresses directly first
- ❌ Using incorrect IP addresses in /etc/hosts

## Hints

1. Start by testing IP addresses directly
2. Map discovered IPs to hostnames in /etc/hosts
3. Use HTTP-based tools (ffuf, curl) instead of DNS tools
4. Admin subdomain contains the flag
5. Flag is in /flag.txt on admin subdomain
