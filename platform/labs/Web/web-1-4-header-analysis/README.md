# Lab 1.4: Header Analysis

## Learning Objectives
- Understand HTTP headers and their security implications
- Identify security headers (CSP, HSTS, X-Frame-Options)
- Detect information disclosure in headers
- Analyze missing security headers
- Capture the flag

## What is Header Analysis?

Header analysis is the process of examining HTTP response headers to:
- Identify security misconfigurations
- Detect information disclosure
- Find missing security headers
- Understand server configuration
- Discover hidden information

HTTP headers can reveal:
- Server software and versions
- Application frameworks
- Security configurations
- Internal infrastructure details
- Debug information

## Solution Walkthrough

### Step 1: Add Hostname to /etc/hosts

Add the target hostname to your `/etc/hosts` file to enable domain name resolution.

**Detailed Steps:**

1. **Open the hosts file with a text editor:**
   ```bash
   sudo nano /etc/hosts
   # Or use: sudo vim /etc/hosts
   ```

2. **Add the hostname mapping** (replace `<target_ip>` with the IP shown in the lab panel):
   ```bash
   <target_ip>    secure.lab
   ```

3. **Save and exit:**
   - In nano: Press `Ctrl+X`, then `Y`, then `Enter`
   - In vim: Press `Esc`, type `:wq`, then `Enter`

4. **Verify the entry was added:**
   ```bash
   cat /etc/hosts | grep secure.lab
   ```
   
   **Expected output:**
   ```
   <target_ip>    secure.lab
   ```

**Troubleshooting:**
- If you get "Permission denied", make sure you're using `sudo`
- Verify the IP address is correct by checking the lab platform

### Step 2: Retrieve HTTP Headers

Get the HTTP response headers to analyze for information disclosure and security configurations.

**Detailed Steps:**

1. **Get headers only (clean output):**
   ```bash
   curl -I http://secure.lab
   ```

   **Command breakdown:**
   - `curl`: HTTP client tool
   - `-I`: Fetch headers only (HEAD request)
   - `http://secure.lab`: Target URL

2. **Get full request/response with headers (verbose):**
   ```bash
   curl -v http://secure.lab
   ```

   **Expected output:**
   ```
   * Connected to secure.lab (<target_ip>) port 80
   > GET / HTTP/1.1
   > Host: secure.lab
   > User-Agent: curl/7.81.0
   > Accept: */*
   >
   < HTTP/1.1 200 OK
   < Server: Apache/2.4.54 (Ubuntu)
   < X-Powered-By: PHP/8.1.0
   ...
   ```

3. **Save headers to file for analysis:**
   ```bash
   curl -I http://secure.lab > headers.txt
   cat headers.txt
   ```

   **Expected output in file:**
   ```
   HTTP/1.1 200 OK
   Server: Apache/2.4.54 (Ubuntu)
   X-Powered-By: PHP/8.1.0
   ...
   ```

**What to look for:**
- All response headers
- Custom headers (starting with `X-`)
- Security headers
- Information disclosure headers

### Step 3: Analyze Standard Headers

Look for standard headers that reveal information:

```bash
curl -I http://secure.lab
```

**Expected headers:**
```
HTTP/1.1 200 OK
Server: Apache/2.4.54 (Ubuntu)
X-Powered-By: PHP/8.1.0
X-Backend-Server: web-server-01.internal.lab
X-Debug-Mode: enabled
X-Application-Version: 1.2.3
X-XSS-Protection: 0
```

**Information disclosed:**
- Server software and version
- PHP version
- Internal server name
- Debug mode enabled
- Application version
- Weak XSS protection

### Step 4: Check for Security Headers

Identify which security headers are present or missing:

**Missing security headers:**
- `X-Frame-Options` - Missing (clickjacking risk)
- `X-Content-Type-Options` - Missing (MIME sniffing risk)
- `Content-Security-Policy` - Missing (XSS risk)
- `Strict-Transport-Security` - Missing (HTTPS enforcement)

**Weak security headers:**
- `X-XSS-Protection: 0` - Disabled (should be "1; mode=block")

### Step 5: Look for Custom Headers

Custom headers often contain hidden information:

```bash
# Check all headers
curl -v http://secure.lab 2>&1 | grep -i "header"

# Check specific endpoint
curl -I http://secure.lab/headers.php
```

### Step 6: Analyze Headers.php Endpoint

Check the special headers endpoint that may contain additional information or the flag.

**Detailed Steps:**

1. **Get headers from headers.php:**
   ```bash
   curl -I http://secure.lab/headers.php
   ```

2. **Expected output:**
   ```
   HTTP/1.1 200 OK
   Server: Apache/2.4.54 (Ubuntu)
   X-Flag-Hint: Check internal server name
   X-Internal-Server: web-server-01.internal.lab
   X-Secret-Key: OCR{h34d3r_4n4lys1s_b4s1c}
   Content-Type: text/html
   ```

3. **Get verbose output for more details:**
   ```bash
   curl -v http://secure.lab/headers.php
   ```

4. **Check if endpoint exists:**
   ```bash
   curl -I http://secure.lab/headers.php
   ```

   - If you get 404, try: `/header.php`, `/header`, `/headers`
   - If you get 403, the endpoint exists but access is forbidden

**Expected headers from headers.php:**
```
X-Flag-Hint: Check internal server name
X-Internal-Server: web-server-01.internal.lab
X-Secret-Key: OCR{h34d3r_4n4lys1s_b4s1c}
```

**What these headers reveal:**
- `X-Flag-Hint`: Hint about where to find the flag
- `X-Internal-Server`: Internal server name (information disclosure)
- `X-Secret-Key`: **THE FLAG!**

### Step 7: Extract the Flag

The flag is in the `X-Secret-Key` header from the headers.php endpoint.

**Detailed Steps:**

1. **Extract just the flag header:**
   ```bash
   curl -I http://secure.lab/headers.php | grep -i "X-Secret-Key"
   ```

   **Expected output:**
   ```
   X-Secret-Key: OCR{h34d3r_4n4lys1s_b4s1c}
   ```

2. **Get all headers and manually look for it:**
   ```bash
   curl -I http://secure.lab/headers.php
   ```

   Scroll through the output to find `X-Secret-Key`.

3. **Extract just the flag value:**
   ```bash
   curl -I http://secure.lab/headers.php | grep -i "X-Secret-Key" | cut -d' ' -f2
   ```

   **Expected output:**
   ```
   OCR{h34d3r_4n4lys1s_b4s1c}
   ```

4. **Alternative: Use browser DevTools:**
   - Navigate to: `http://secure.lab/headers.php`
   - Open DevTools (F12)
   - Go to Network tab
   - Click on the request
   - Check Response Headers
   - Look for `X-Secret-Key`

**Flag:**
```
OCR{h34d3r_4n4lys1s_b4s1c}
```

**Troubleshooting:**
- If headers.php doesn't exist, check other endpoints: `/api/headers`, `/admin/headers`
- Try different file extensions: `.php`, `.html`, `.txt`
- Check if flag is in a different header: `X-Flag`, `X-Key`, `X-Token`

### Step 8: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{h34d3r_4n4lys1s_b4s1c}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Successfully added hostname to /etc/hosts
- ✅ Retrieved HTTP headers from the web server
- ✅ Analyzed standard headers for information disclosure
- ✅ Checked for security headers (missing or weak)
- ✅ Looked for custom headers
- ✅ Checked headers.php endpoint
- ✅ Extracted flag from X-Secret-Key header
- ✅ Verified flag format is correct: `OCR{...}`

## Alternative Tools

### Browser DevTools

1. **Open website** in browser
2. **Open DevTools** (F12)
3. **Network tab** → Select request → **Headers tab**
4. **Response Headers** section shows all headers

### Burp Suite

1. **Intercept request** in Burp Suite
2. **Forward** request
3. **Response** tab → **Headers** section
4. Analyze all response headers

### Online Header Analyzers

- **SecurityHeaders.com**: https://securityheaders.com
- **Observatory by Mozilla**: https://observatory.mozilla.org

### Custom Script

```bash
#!/bin/bash
URL="http://secure.lab"
echo "Analyzing headers for: $URL"
echo "================================"
curl -I "$URL" | while IFS= read -r line; do
    echo "$line"
done
```

## Important Security Headers

### X-Frame-Options
- **Purpose**: Prevents clickjacking
- **Values**: `DENY`, `SAMEORIGIN`
- **Risk if missing**: Clickjacking attacks

### X-Content-Type-Options
- **Purpose**: Prevents MIME type sniffing
- **Values**: `nosniff`
- **Risk if missing**: MIME confusion attacks

### Content-Security-Policy (CSP)
- **Purpose**: Prevents XSS attacks
- **Values**: Complex policy string
- **Risk if missing**: XSS vulnerabilities

### Strict-Transport-Security (HSTS)
- **Purpose**: Forces HTTPS connections
- **Values**: `max-age=31536000; includeSubDomains`
- **Risk if missing**: Man-in-the-middle attacks

### X-XSS-Protection
- **Purpose**: Enables browser XSS filter
- **Values**: `1; mode=block`
- **Risk if disabled**: XSS attacks

### Referrer-Policy
- **Purpose**: Controls referrer information
- **Values**: `no-referrer`, `strict-origin-when-cross-origin`
- **Risk if missing**: Information leakage

## Information Disclosure Headers

### Server Information
- `Server`: Web server software and version
- `X-Powered-By`: Server-side technology
- `X-AspNet-Version`: ASP.NET version

### Application Information
- `X-Application-Version`: Application version
- `X-Framework`: Framework name and version
- `X-Generator`: CMS or framework generator

### Infrastructure Information
- `X-Backend-Server`: Internal server names
- `X-Load-Balancer`: Load balancer information
- `X-Forwarded-For`: Proxy information

### Debug Information
- `X-Debug-Mode`: Debug mode status
- `X-Error-Details`: Error information
- `X-Stack-Trace`: Stack trace information

## Hints

1. Start by retrieving all HTTP headers with `curl -I`
2. Look for custom headers that might contain information
3. Check the `/headers.php` endpoint for special headers
4. Analyze both standard and custom headers
5. Look for headers with "Secret", "Key", "Flag" in the name
6. Use `-v` flag for verbose output
7. Check multiple endpoints for different headers
8. Flag is in a custom header from headers.php endpoint

## Common Mistakes

- Not checking all headers, only standard ones
- Missing custom headers that contain information
- Not checking multiple endpoints
- Not using verbose mode to see all headers
- Assuming flag is in response body, not headers
- Not analyzing security headers for misconfigurations
- Missing headers from different endpoints

## Educational Context

### Why Header Analysis Matters

- **Information Disclosure**: Headers can leak sensitive information
- **Security Misconfigurations**: Missing headers indicate weak security
- **Attack Planning**: Headers reveal attack surface
- **Compliance**: Security headers are often required

### Security Header Best Practices

1. **Implement Security Headers**: Add all recommended security headers
2. **Remove Information Headers**: Remove or minimize information disclosure
3. **Regular Audits**: Check headers regularly for issues
4. **Use Security Tools**: Tools like SecurityHeaders.com help identify issues
5. **Test Headers**: Verify headers are working correctly

### Real-World Examples

- **Information Disclosure**: Server version in headers → Known vulnerabilities
- **Missing CSP**: XSS attacks possible
- **Missing HSTS**: Man-in-the-middle attacks possible
- **Debug Headers**: Reveal internal structure

## Further Reading

- OWASP: Secure Headers
- SecurityHeaders.com: Header Analysis
- Mozilla Observatory: Security Analysis
- MDN: HTTP Headers

