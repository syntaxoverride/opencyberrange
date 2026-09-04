# Lab 1.1: Basic Directory Enumeration

## Learning Objectives
- Understand directory enumeration concepts
- Use gobuster to discover hidden directories
- Identify common web directories
- Capture the flag

## What is Directory Enumeration?

Directory enumeration is the process of discovering hidden directories and files on a web server that are not linked from the main page. These hidden directories often contain:
- Admin panels
- Backup files
- Configuration files
- API endpoints
- Sensitive data

## Solution Walkthrough

### Step 1: Add Hostname to /etc/hosts

First, add the target hostname to your `/etc/hosts` file. This allows your system to resolve the `.lab` domain name to the target IP address.

**Detailed Steps:**

1. **Open the hosts file with a text editor:**
   ```bash
   sudo nano /etc/hosts
   # Or use: sudo vim /etc/hosts
   ```

2. **Add the hostname mapping** (replace `<target_ip>` with the IP shown in the lab panel):
   ```bash
   <target_ip>    recon.lab
   ```

3. **Save and exit:**
   - In nano: Press `Ctrl+X`, then `Y`, then `Enter`
   - In vim: Press `Esc`, type `:wq`, then `Enter`

4. **Verify the entry was added:**
   ```bash
   cat /etc/hosts | grep recon.lab
   ```
   
   **Expected output:**
   ```
   <target_ip>    recon.lab
   ```

**Troubleshooting:**
- If you get "Permission denied", make sure you're using `sudo`
- Verify the IP address is correct by checking the lab platform
- Ensure there are no typos in the hostname

### Step 2: Verify Web Server Access

Before starting enumeration, verify that the web server is accessible and responding.

**Detailed Steps:**

1. **Test basic connectivity:**
   ```bash
   curl http://recon.lab
   ```

2. **Check the HTTP response:**
   ```bash
   curl -I http://recon.lab
   ```

   **Expected output:**
   ```
   HTTP/1.1 200 OK
   Server: Apache/2.4.54
   Content-Type: text/html
   Content-Length: 1234
   ```

3. **Verify in browser (optional):**
   - Open your browser
   - Navigate to: `http://recon.lab`
   - You should see a welcome page or default web page

**What to look for:**
- Status code 200 means the server is responding
- Any other status code (404, 403, 500) indicates an issue
- If you get "Connection refused" or timeout, check the IP address and ensure the lab is running

### Step 3: Directory Enumeration with Gobuster

Use gobuster to systematically test common directory names and discover hidden directories.

**Detailed Steps:**

1. **Verify gobuster is installed:**
   ```bash
   which gobuster
   # Should output: /usr/bin/gobuster or similar path
   ```

2. **Check wordlist availability:**
   ```bash
   ls -la /usr/share/wordlists/dirb/common.txt
   # If not found, try: /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
   ```

3. **Run basic directory enumeration:**
   ```bash
   gobuster dir -u http://recon.lab -w /usr/share/wordlists/dirb/common.txt
   ```

   **Command breakdown:**
   - `gobuster dir`: Run gobuster in directory enumeration mode
   - `-u http://recon.lab`: Target URL to scan
   - `-w /usr/share/wordlists/dirb/common.txt`: Wordlist file containing directory names to test

4. **Run with optimized settings (recommended):**
   ```bash
   gobuster dir -u http://recon.lab -w /usr/share/wordlists/dirb/common.txt -t 50 -x txt,php,html
   ```

   **Additional options:**
   - `-t 50`: Use 50 threads for faster scanning (default is 10)
   - `-x txt,php,html`: Also test for files with these extensions

**Gobuster Options Explained:**
- `-u`: Target URL (required)
- `-w`: Wordlist file path (required)
- `-t`: Number of threads (optional, default: 10, higher = faster but more aggressive)
- `-x`: File extensions to test (optional, e.g., `-x txt,php,html,bak`)
- `-k`: Skip SSL certificate verification (for HTTPS)
- `-s`: Status codes to consider valid (default: 200,204,301,302,307,401,403)

**Expected output during scan:**
```
===============================================================
Gobuster v3.8
by OJ Reeves (@TheColonial) & Christian Mehlmauer (@firefart)
===============================================================
[+] Url:                     http://recon.lab
[+] Method:                  GET
[+] Threads:                 50
[+] Wordlist:                /usr/share/wordlists/dirb/common.txt
[+] Negative Status codes:   404
[+] User Agent:              gobuster/3.8
[+] Extensions:              txt,php,html
[+] Timeout:                 10s
===============================================================
Starting gobuster in directory enumeration mode
===============================================================
/admin                (Status: 301) [Size: 308] [--> http://recon.lab/admin/]
/backup               (Status: 301) [Size: 309] [--> http://recon.lab/backup/]
/config               (Status: 301) [Size: 309] [--> http://recon.lab/config/]
/index.html           (Status: 200) [Size: 100]
===============================================================
Finished
===============================================================
```

**What the output means:**
- `/admin (Status: 301) [Size: 308] [--> http://recon.lab/admin/]`: Directory found, Apache redirects to directory with trailing slash
- Status 200 = Directory/file exists and is directly accessible
- Status 301/302 = Redirect (directory exists, server redirects to canonical URL with trailing slash)
- Status 403 = Directory exists but access is forbidden
- **Both Status 200 and 301/302 indicate a directory exists** - 301 redirects are normal Apache behavior

### Step 4: Analyze Results

Carefully review the gobuster output to identify which directories were discovered.

**Detailed Steps:**

1. **Review all discovered directories:**
   - Look for directories with Status: 200 or 301/302 (both indicate directory exists)
   - Status 301/302 means Apache redirects to the directory with a trailing slash (normal behavior)
   - Note the sizes - larger sizes may indicate more content
   - Pay attention to directory names that suggest sensitive content

2. **Prioritize interesting directories:**
   - `/admin` - Often contains admin panels or sensitive files
   - `/backup` - May contain backup files with sensitive data
   - `/config` - Configuration files may contain credentials
   - `/api` - API endpoints may have vulnerabilities

3. **Document your findings:**
   ```
   Discovered Directories:
   - /admin (301) - Redirects to /admin/
   - /backup (301) - Redirects to /backup/
   - /config (301) - Redirects to /config/
   ```

**Expected findings for this lab:**
```
/admin                (Status: 301) [Size: 308] [--> http://recon.lab/admin/]
/backup               (Status: 301) [Size: 309] [--> http://recon.lab/backup/]
/config               (Status: 301) [Size: 309] [--> http://recon.lab/config/]
/index.html           (Status: 200) [Size: 100]
```

**Note:** Status 301 redirects are normal and expected when accessing directories without trailing slashes. Apache automatically redirects `/admin` to `/admin/` to ensure proper directory access.

### Step 5: Access Hidden Directory

Manually verify and explore each discovered directory to find the flag.

**Detailed Steps:**

1. **Check the admin directory listing:**
   ```bash
   curl http://recon.lab/admin/
   ```

   **Expected output:**
   ```
   <html>
   <head><title>Admin Directory</title></head>
   <body>
   <h1>Admin Area</h1>
   <ul>
   <li><a href="flag.txt">flag.txt</a></li>
   </ul>
   </body>
   </html>
   ```

2. **Check for the flag file directly:**
   ```bash
   curl http://recon.lab/admin/flag.txt
   ```

   **Alternative: Use browser:**
   - Navigate to: `http://recon.lab/admin/`
   - Look for `flag.txt` link or file listing
   - Click on `flag.txt` or navigate to: `http://recon.lab/admin/flag.txt`

3. **If flag.txt is not visible, try common variations:**
   ```bash
   curl http://recon.lab/admin/flag
   curl http://recon.lab/admin/flag.txt
   curl http://recon.lab/admin/.flag.txt
   curl http://recon.lab/admin/FLAG.txt
   ```

4. **Check other discovered directories if needed:**
   ```bash
   curl http://recon.lab/backup/
   curl http://recon.lab/config/
   ```

**Troubleshooting:**
- If you get 404, the file might be in a subdirectory
- Try directory listing: `curl http://recon.lab/admin/` (may show file list)
- Check for case sensitivity: `flag.txt` vs `Flag.txt` vs `FLAG.txt`

### Step 6: Retrieve Flag

Extract and verify the flag from the discovered location.

**Detailed Steps:**

1. **Retrieve the flag:**
   ```bash
   curl http://recon.lab/admin/flag.txt
   ```

2. **Expected flag output:**
   ```
   OCR{d1r3ct0ry_3num3r4t10n_b4s1c}
   ```

3. **Verify flag format:**
   - Flag should start with `OCR{` and end with `}`
   - Contains alphanumeric characters and underscores
   - Copy the entire flag including `OCR{}` brackets

4. **Alternative retrieval methods:**
   ```bash
   # Save flag to file
   curl http://recon.lab/admin/flag.txt -o flag.txt
   cat flag.txt
   
   # Using wget
   wget http://recon.lab/admin/flag.txt
   cat flag.txt
   
   # Using browser
   # Simply copy the text from the browser
   ```

**Flag format verification:**
- ✅ Correct: `OCR{d1r3ct0ry_3num3r4t10n_b4s1c}`
- ❌ Wrong: `d1r3ct0ry_3num3r4t10n_b4s1c` (missing OCR{} wrapper)
- ❌ Wrong: `OCR{d1r3ct0ry_3num3r4t10n_b4s1c` (missing closing brace)

**Success Criteria:**
- ✅ Successfully added hostname to /etc/hosts
- ✅ Verified web server is accessible
- ✅ Ran gobuster and discovered directories
- ✅ Found /admin directory
- ✅ Retrieved flag.txt from /admin/
- ✅ Flag format is correct: `OCR{...}`

## Alternative Tools

### Dirb
```bash
dirb http://recon.lab /usr/share/wordlists/dirb/common.txt
```

### Dirbuster (GUI)
- Launch DirBuster
- Enter target URL: `http://recon.lab`
- Select wordlist
- Start scan

### FFUF
```bash
ffuf -w /usr/share/wordlists/dirb/common.txt -u http://recon.lab/FUZZ
```

## Common Directories to Look For

- `/admin` - Admin panels
- `/backup` - Backup files
- `/config` - Configuration files
- `/api` - API endpoints
- `/test` - Test directories
- `/dev` - Development files
- `/old` - Old versions
- `/tmp` - Temporary files

## Hints

1. Start with common wordlists like `/usr/share/wordlists/dirb/common.txt`
2. Look for status code 200 (success) in results
3. Check discovered directories manually
4. Flag is in the `/admin` directory
5. Use browser or curl to access files

## Common Mistakes

- Not adding hostname to /etc/hosts first
- Using wrong wordlist path
- Not checking discovered directories manually
- Forgetting to look for files, not just directories
- Not trying different file extensions (.txt, .bak, etc.)

## Educational Context

### Why Directory Enumeration Matters

- **Information Disclosure**: Hidden directories often contain sensitive information
- **Attack Surface**: More directories = more potential vulnerabilities
- **Real-World**: Many real web applications have hidden admin panels or backup files

### Tools Comparison

- **Gobuster**: Fast, modern, written in Go
- **Dirb**: Older but reliable, written in C
- **DirBuster**: GUI tool, good for beginners
- **FFUF**: Very fast, flexible, written in Go

## Further Reading

- OWASP: Testing for Directory Traversal
- Gobuster documentation: https://github.com/OJ/gobuster
- Common web directories: https://github.com/danielmiessler/SecLists

