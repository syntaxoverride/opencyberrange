# Exercise 2.3: HTTP Session Hijacking

## Before You Begin

Exercises 2.1 and 2.2 focused on credential theft from cleartext protocols; FTP and
Telnet transmit passwords in plaintext, and an attacker with a packet capture can
read them directly. this exercise introduces a different attack vector: **session
hijacking**. Instead of stealing a password, the attacker steals an active session
token and uses it to impersonate an already-authenticated user.

All analysis in this exercise is performed with `tshark` over an SSH connection. You
SSH into the analyst workstation at `<target_ip>`, the address shown on the launch page.

## Scenario

A patient has reported suspicious activity on MediCare's patient portal; their
medical records were accessed from an unfamiliar location. Marcus Thompson, the
lead security analyst, suspects session hijacking: someone intercepted and reused
a valid session cookie to impersonate the authenticated user. Network monitoring
captured the relevant traffic during the incident window. Your task is to analyze
the captured traffic, confirm the attack, identify the attacker, and determine
what data was accessed.

## Your Objectives

- SSH into the analysis container
- Identify when session cookies are issued by the server
- Track cookie usage across different source IPs
- Detect the session hijacking; the same cookie used from a different IP
- Determine what the attacker accessed
- Find and submit the flag

## Background: HTTP Session Management and Hijacking

Web applications use **cookies** to track logged-in users. The typical flow works
as follows: a user submits their credentials via a login form, and the server
validates them. If authentication succeeds, the server responds with a
`Set-Cookie` header containing a **session ID**: a unique token that identifies
that user's session. The browser stores this cookie and includes it automatically
in every subsequent request to the same site. The server checks the cookie on
each request and, if valid, grants access without requiring the user to log in
again.

**Session hijacking** occurs when an attacker obtains a valid session cookie and
replays it from their own machine. The attacker does not need the user's password.
The server receives the cookie, validates it, and grants access as though the
request came from the legitimate user. There are several ways an attacker can
obtain the cookie:

- **Network sniffing**: if the application uses HTTP instead of HTTPS, cookies
  travel in cleartext and can be captured by anyone monitoring the network
- **Cross-site scripting (XSS)**: malicious JavaScript injected into the page
  can read cookies and exfiltrate them to the attacker
- **Malware**: software on the victim's machine can extract cookies from the
  browser's storage

The primary detection indicator is straightforward: the **same session cookie
appearing from two different source IPs**. A legitimate user does not typically
change IP addresses mid-session.

Prevention relies on several layers. **HTTPS** encrypts all traffic, including
cookies, so network sniffing yields nothing usable. The **Secure** cookie flag
tells the browser to only send the cookie over HTTPS connections. The
**HttpOnly** flag prevents JavaScript from reading the cookie, blocking XSS-based
theft. **IP binding** on the server side rejects a cookie if the source IP
changes from the one that originally authenticated.

## Walkthrough

### Step 1: Launch the Exercise

Start the lab environment from the launcher. Wait for the container to initialize
before proceeding.

### Step 2: Connect to the Analysis Container

!!! kali "Connect to the analysis container"
    Run this from your Kali terminal. Replace `<target_ip>` with the address shown on the launch page. The SSH session lands you on the staged analyst host.

    ```bash
    ssh analyst@<target_ip>
    ```

    Enter the password `MediCare2024#` when prompted.

!!! target "Confirm the capture file is present"
    Run this on the analysis container after the SSH session connects. The listing verifies the PCAP is staged before you start.

    ```bash
    ls captures/
    ```

    You should see `session-hijack.pcap`.

### Step 3: Get a Protocol Overview

!!! target "Get a protocol hierarchy overview"
    Run this on the analysis container. The `-z io,phs` option displays a protocol hierarchy with packet counts so you can see which protocols carry the session activity.

    ```bash
    tshark -r captures/session-hijack.pcap -q -z io,phs
    ```

    You should see HTTP traffic on port 80, which is where the session activity takes place. Note the absence of TLS; all traffic is unencrypted.

### Step 4: Find Set-Cookie Headers

!!! target "Find Set-Cookie headers"
    Run this on the analysis container. The `http.set_cookie` filter shows every response where the server issued a session cookie.

    ```bash
    tshark -r captures/session-hijack.pcap -Y "http.set_cookie" \
      -T fields -e frame.number -e ip.src -e ip.dst -e http.set_cookie
    ```

    Note which client IPs received cookies and what the cookie values are.

---

**Record Your Findings**

- Which IP addresses received `Set-Cookie` headers from the server?
- What is the session cookie name and value?
- In which frame number was the cookie first issued?

---

### Step 5: Track All Cookie Usage

!!! target "List every request carrying a cookie"
    Run this on the analysis container. The `http.cookie` filter reveals every HTTP request where a client presented a session cookie.

    ```bash
    tshark -r captures/session-hijack.pcap -Y "http.cookie" \
      -T fields -e frame.number -e ip.src -e ip.dst -e http.request.uri -e http.cookie
    ```

    Look at the source IPs; if only the legitimate user is browsing, you should see a single IP. If a second IP appears using the same cookie, that is your hijacking indicator.

!!! target "Locate the original login request"
    Run this on the analysis container. The filter finds the POST to the login endpoint, confirming which IP actually authenticated.

    ```bash
    tshark -r captures/session-hijack.pcap \
      -Y "http.request.method == POST and http.request.uri contains login" \
      -T fields -e frame.number -e ip.src -e ip.dst -e http.request.uri
    ```

    The source IP of this POST is the legitimate user who logged in.

### Step 6: Identify the Hijacking

!!! target "Isolate the IPs sharing one cookie"
    Run this on the analysis container. The filter pins one specific session cookie and lists the unique source IPs that presented it.

    ```bash
    tshark -r captures/session-hijack.pcap \
      -Y 'http.cookie contains "SESSIONID=abc123def456"' \
      -T fields -e ip.src | sort -u
    ```

    If two different IPs appear, the session was hijacked. The IP that performed the login is the legitimate user; the other is the attacker.

---

**Record Your Findings**

- Legitimate user IP: _______________
- Attacker IP: _______________
- Shared session cookie value: _______________
- Approximate time gap between the legitimate session and the attacker's first request: _______________

---

### Step 7: Examine What the Attacker Accessed

!!! target "Examine the attacker's activity"
    Run this on the analysis container. The filter scopes the capture to the attacker's IP so you can read every URI they requested.

    ```bash
    tshark -r captures/session-hijack.pcap \
      -Y "ip.src == 10.0.1.87 and http" \
      -T fields -e frame.number -e http.request.method -e http.request.uri -e http.cookie
    ```

    Review the URIs the attacker requested. You should see requests to endpoints such as `/api/medical-records`: the attacker used the hijacked session to access sensitive patient data. Note that the attacker never visited `/login` and never performed a POST to authenticate. They went straight to protected resources using the stolen cookie.

### Step 8: Follow the Attacker's TCP Stream

To see the full request and response content, follow one of the attacker's TCP
streams. First, identify the TCP stream number from one of the attacker's
packets.

!!! target "Follow the attacker's TCP stream"
    Run this on the analysis container. Replace `<stream_number>` with the stream index you identified to reassemble the full request and response content.

    ```bash
    tshark -r captures/session-hijack.pcap -q -z follow,tcp,ascii,<stream_number>
    ```

    In the stream output, examine the cookie value closely:

```
SESSIONID=abc123def456OCR{<flag_here>}xyz789
```

The flag is embedded in the session cookie value itself in `OCR{<flag_here>}` format.

## Analysis Questions

**1. How did you determine which IP was the legitimate user and which was the
attacker?**

> The legitimate user (10.0.1.15) performed the login POST request and received
> the Set-Cookie header from the server. The attacker (10.0.1.87) never logged
> in; they appeared approximately seven minutes later using the same cookie
> without any prior authentication. The lack of a login sequence from the
> attacker's IP is the key indicator.

**2. The attack happened over HTTP (port 80). How would HTTPS have prevented
it?**

> HTTPS encrypts all traffic including cookies. An attacker sniffing the network
> would see only encrypted data and could not extract the session cookie.
> Combined with the Secure cookie flag, which prevents the browser from sending
> the cookie over HTTP, HTTPS eliminates network-based session hijacking.

**3. What cookie attributes would make session hijacking harder even without
HTTPS?**

> HttpOnly prevents JavaScript from reading the cookie, which blocks XSS-based
> theft. SameSite=Strict prevents the cookie from being sent in cross-site
> requests, which blocks CSRF. Short session timeouts reduce the window of
> opportunity for an attacker to reuse a stolen cookie. IP binding on the server
> side rejects the cookie if the source IP changes from the one that originally
> authenticated. None of these fully replace HTTPS, but they add defense in
> depth.

## Key Takeaways

- Session hijacking steals access without stealing credentials; the attacker
  replays a valid session cookie to impersonate an authenticated user
- The telltale sign is the same session cookie appearing from two different
  source IPs
- tshark can track cookie issuance (`Set-Cookie` response headers) and cookie
  usage (`Cookie` request headers) across the entire capture
- HTTP transmits cookies in cleartext, making network-based session theft trivial
- HTTPS with Secure and HttpOnly cookie flags is the primary defense against
  session hijacking
