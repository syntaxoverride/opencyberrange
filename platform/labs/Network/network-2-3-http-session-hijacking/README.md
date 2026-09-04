# Network Lab 2-3: HTTP Session Cookie Extraction

## Lab Overview

**Difficulty**: Intermediate
**Category**: Network Security
**Duration**: 60 minutes

### Scenario

Marcus Thompson, MediCare Health Systems' Security Analyst, received an alert from the patient portal about suspicious activity. A patient reported seeing their medical records being accessed from an unfamiliar location. Marcus suspects **session hijacking** - someone may have stolen and reused a valid session cookie to impersonate the authenticated user.

Your task is to analyze the captured network traffic from the patient portal server to identify the session hijacking attack, find the stolen session cookie, and understand how the attacker gained unauthorized access.

### Learning Objectives

- Understand HTTP cookie-based session management
- Identify session hijacking attacks in network traffic
- Extract and analyze session cookies from HTTP headers
- Recognize the security risks of unencrypted HTTP traffic
- Learn security best practices for session management

---

## Lab Setup

### Starting the Lab

1. **Start the lab environment**:
   ```bash
   cd labs/Network/network-2-3-http-session-hijacking
   docker-compose up -d
   ```

2. **Connect via SSH**:
   ```bash
   ssh analyst@<target_ip>
   ```
   **Password**: `MediCare2024#`

3. **Verify the capture file exists**:
   ```bash
   ls -lh captures/
   ```
   You should see `session-hijack.pcap`

---

## Analysis Walkthrough

### Step 1: Initial PCAP Inspection

First, let's get basic information about the capture:

```bash
# View basic statistics
tshark -r captures/session-hijack.pcap -q -z io,phs

# Count total packets
tshark -r captures/session-hijack.pcap -q -z io,stat,0
```

You'll see a mix of HTTP, DNS, and TCP traffic spanning several hours.

### Step 2: Understanding HTTP Session Management

**Background**: Web applications use cookies to maintain user sessions. When you log in:

1. **Client → Server**: POST request with credentials
2. **Server → Client**: HTTP 200 response with `Set-Cookie` header establishing session
3. **Client → Server**: Subsequent requests include `Cookie` header with session ID
4. **Session Hijacking**: Attacker obtains the session cookie and reuses it from a different location

### Step 3: Finding Session Cookie Establishment

Let's find when session cookies are set:

```bash
# Filter for Set-Cookie headers
tshark -r captures/session-hijack.pcap -Y "http.set_cookie" -T fields \
  -e frame.number -e ip.src -e ip.dst -e http.set_cookie
```

You should see output like:
```
23    192.168.100.10    10.0.1.15    SESSIONID=abc123def456...; Path=/; HttpOnly
156   192.168.100.10    10.0.1.23    SESSIONID=xyz789abc123...; Path=/; HttpOnly
```

**Key observation**: The server (`192.168.100.10`) sends session cookies to clients after successful login.

### Step 4: Examining Login Sequence

Let's look at the complete login sequence for the first user:

```bash
# Find the login POST request and response
tshark -r captures/session-hijack.pcap -Y "http.request.method == POST and http.request.uri contains login" \
  -T fields -e frame.number -e ip.src -e ip.dst -e http.request.uri
```

Now view the full HTTP stream for that login:

```bash
# Follow HTTP stream (replace stream number based on your findings)
tshark -r captures/session-hijack.pcap -q -z follow,http,ascii,0
```

You'll see:
- POST request with username/password
- Server response with `Set-Cookie: SESSIONID=...`

**Important**: Note the SESSIONID value and the client IP address (`10.0.1.15`).

### Step 5: Tracking Cookie Usage

Now let's see all requests that use cookies:

```bash
# Show all HTTP requests with Cookie headers
tshark -r captures/session-hijack.pcap -Y "http.cookie" -T fields \
  -e frame.number -e ip.src -e ip.dst -e http.request.uri -e http.cookie
```

Look for patterns:
- Which IP addresses are making requests?
- Are the same cookies being used from different IPs?

### Step 6: Identifying Session Hijacking

**Critical Analysis**: Look for the SESSIONID from Step 4 being used by different source IPs.

```bash
# Extract unique source IPs using specific SESSIONID
tshark -r captures/session-hijack.pcap -Y 'http.cookie contains "SESSIONID=abc123def456"' \
  -T fields -e ip.src | sort -u
```

**Expected finding**: The same session cookie used by:
- `10.0.1.15` (legitimate user - received the cookie)
- `10.0.1.87` (attacker - using stolen cookie!)

### Step 7: Analyzing the Attacker's Activity

Let's examine what the attacker accessed:

```bash
# Filter for HTTP requests from the attacker's IP
tshark -r captures/session-hijack.pcap -Y "ip.src == 10.0.1.87 and http" \
  -T fields -e frame.number -e http.request.method -e http.request.uri -e http.cookie
```

You'll see the attacker:
1. Makes DNS query for `portal.medicare.local`
2. Establishes TCP connection to the server
3. Uses the stolen SESSIONID cookie
4. Accesses sensitive endpoints like `/api/medical-records`

### Step 8: Extracting the Flag

Follow the HTTP stream of the attacker's request to see the response:

```bash
# Find the attacker's request stream number
tshark -r captures/session-hijack.pcap -Y "ip.src == 10.0.1.87 and http.request" \
  -T fields -e frame.number -e tcp.stream | head -1
```

Then follow that specific TCP stream:

```bash
# Replace X with the stream number from above
tshark -r captures/session-hijack.pcap -q -z follow,tcp,ascii,X
```

**Alternative using Wireshark** (if X forwarding is available):

```bash
wireshark captures/session-hijack.pcap &
```

In Wireshark:
1. Filter: `ip.src == 10.0.1.87 and http`
2. Right-click on the medical records request
3. Select "Follow → HTTP Stream"
4. Look for the flag in the response JSON

**Flag Location**: The flag appears in:
- The SESSIONID cookie value itself: `SESSIONID=abc123def456OCR{s3ss10n_c00k13_st0l3n}xyz789`
- The server's response to the attacker's hijacked request

### Step 9: Evidence Summary

Complete timeline of the attack:

```bash
# Get chronological view of the session hijacking
tshark -r captures/session-hijack.pcap -Y "(http.set_cookie contains SESSIONID) or \
  (http.cookie contains abc123def456)" -T fields -e frame.time -e ip.src -e ip.dst \
  -e http.request.method -e http.request.uri -e http.set_cookie -e http.cookie
```

**Attack Timeline**:
1. **T+0**: Legitimate user `10.0.1.15` logs in to portal
2. **T+0.1s**: Server sends `Set-Cookie: SESSIONID=abc123def456OCR{s3ss10n_c00k13_st0l3n}xyz789`
3. **T+10s**: Legitimate user accesses dashboard using cookie
4. **T+45s**: Legitimate user accesses appointments using cookie
5. **T+7min**: **ATTACKER** `10.0.1.87` uses the same cookie to access medical records!
6. **T+7min 8s**: Attacker uses cookie again to view prescriptions

---

## Understanding the Attack

### How Session Hijacking Works

1. **Cookie Theft**: Attacker intercepts or steals a valid session cookie through:
   - Network sniffing (if using unencrypted HTTP)
   - Cross-site scripting (XSS)
   - Malware on victim's device
   - Man-in-the-middle attack

2. **Cookie Reuse**: Attacker injects the stolen cookie into their own HTTP requests

3. **Unauthorized Access**: Server accepts the valid cookie and grants access without requiring authentication

### Red Flags in This Scenario

- **Different source IPs**: Same cookie used from `10.0.1.15` and `10.0.1.87`
- **No login**: Attacker never performed login, directly used the cookie
- **Sensitive data access**: Attacker accessed `/api/medical-records` with stolen session
- **Unencrypted HTTP**: Traffic sent over HTTP (port 80) instead of HTTPS (port 443)

---

## Security Best Practices

### 1. Use HTTPS Everywhere
```http
Set-Cookie: SESSIONID=...; Path=/; Secure; HttpOnly; SameSite=Strict
```
- **Secure flag**: Cookie only sent over HTTPS
- **HttpOnly flag**: JavaScript cannot access cookie (prevents XSS)
- **SameSite flag**: Prevents CSRF attacks

### 2. Additional Session Security

- **Session timeouts**: Expire sessions after inactivity
- **IP binding**: Tie sessions to originating IP (with caveats for mobile users)
- **User-Agent validation**: Detect if browser fingerprint changes
- **Multi-factor authentication**: Require additional verification for sensitive actions
- **Session regeneration**: Issue new session ID after login

### 3. Detection and Monitoring

- **Anomaly detection**: Alert on session use from multiple IPs
- **Geolocation tracking**: Flag impossible travel scenarios
- **Rate limiting**: Limit requests per session
- **Audit logging**: Log all session activities with IP addresses

---

## Questions for Reflection

1. What specific HTTP headers revealed the session hijacking?
2. How could HTTPS have prevented this attack?
3. What other security controls could detect or prevent session hijacking?
4. Why is the `HttpOnly` cookie flag important?
5. How would you detect this attack in real-time?

---

## Cleanup

When you're finished:

```bash
# Exit SSH session
exit

# Stop the lab container
docker-compose down
```

---

## Flag Format

The flag follows the format: `OCR{s3ss10n_c00k13_st0l3n}`

**Where to find it**:
- Embedded in the stolen SESSIONID cookie value
- Present in the server's response to the attacker's hijacked session request

---

## Additional Resources

- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [RFC 6265: HTTP State Management Mechanism](https://tools.ietf.org/html/rfc6265)
- [Wireshark HTTP Analysis](https://wiki.wireshark.org/HTTP)
- [Session Hijacking Prevention](https://owasp.org/www-community/attacks/Session_hijacking_attack)

---

## Lab Author Notes

This lab demonstrates the critical importance of:
- Encrypting all web traffic with HTTPS/TLS
- Implementing proper cookie security attributes
- Monitoring for anomalous session usage patterns
- Understanding how session management works at the protocol level

Session hijacking remains a serious threat in modern web applications, particularly when security best practices are not followed. This lab provides hands-on experience identifying these attacks in network traffic.
