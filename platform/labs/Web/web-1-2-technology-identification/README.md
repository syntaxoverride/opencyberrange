# Lab 1.2: Technology Identification

## Learning Objectives
- Understand technology identification concepts
- Use Wappalyzer and browser DevTools to identify technologies
- Analyze HTTP headers for server information
- Identify web frameworks and CMS platforms
- Capture the flag

## What is Technology Identification?

Technology identification is the process of determining what technologies, frameworks, and software are running on a web application. This information is crucial for:
- Understanding the attack surface
- Finding known vulnerabilities
- Selecting appropriate exploitation tools
- Planning attack strategies

## Solution Walkthrough

### Step 1: Add Hostname to /etc/hosts

Add the target hostname to your `/etc/hosts` file to enable domain name resolution.

**Detailed Steps:**

1. **Open the hosts file with a text editor:**
   ```bash
   sudo nano /etc/hosts
   # Or use: sudo vim /etc/hosts
   ```

2. **Add the hostname mapping** (replace `<target_ip>` with your actual target IP from the lab platform):
   ```bash
   <target_ip>    target.lab
   ```

3. **Save and exit:**
   - In nano: Press `Ctrl+X`, then `Y`, then `Enter`
   - In vim: Press `Esc`, type `:wq`, then `Enter`

4. **Verify the entry was added:**
   ```bash
   cat /etc/hosts | grep target.lab
   ```
   
   **Expected output:**
   ```
   <target_ip>    target.lab
   ```

**Troubleshooting:**
- If you get "Permission denied", make sure you're using `sudo`
- Verify the IP address is correct by checking the lab platform
- Ensure there are no typos in the hostname

### Step 2: Initial Web Server Access

Access the web server to see what's running and get initial information.

**Detailed Steps:**

1. **Test basic connectivity:**
   ```bash
   curl http://target.lab
   ```

2. **Get HTTP headers only:**
   ```bash
   curl -I http://target.lab
   ```

   **Expected output:**
   ```
   HTTP/1.1 200 OK
   Server: Apache/2.4.54
   X-Powered-By: PHP/8.1.0
   Content-Type: text/html; charset=UTF-8
   Content-Length: 1234
   ```

3. **Open in browser (optional):**
   - Open your browser
   - Navigate to: `http://target.lab`
   - You should see a web page (possibly WordPress or similar)

**What to observe:**
- Status code 200 means the server is responding
- Initial headers may reveal technology information
- The page content may show framework-specific elements

### Step 3: Analyze HTTP Headers

Examine the HTTP response headers in detail to identify technologies.

**Detailed Steps:**

1. **Get full headers with verbose output:**
   ```bash
   curl -v http://target.lab 2>&1 | grep -i "server\|powered\|framework\|x-"
   ```

   **Command breakdown:**
   - `curl -v`: Verbose mode (shows headers)
   - `2>&1`: Redirects stderr to stdout
   - `grep -i`: Case-insensitive search for technology-related headers

2. **Get all headers:**
   ```bash
   curl -I http://target.lab
   ```

   **Expected output:**
   ```
   HTTP/1.1 200 OK
   Server: Apache/2.4.54
   X-Powered-By: PHP/8.1.0
   X-Framework: WordPress/6.2.0
   X-Content-Type-Options: nosniff
   Content-Type: text/html; charset=UTF-8
   ```

3. **Save headers to file for analysis:**
   ```bash
   curl -I http://target.lab > headers.txt
   cat headers.txt
   ```

**Look for these headers:**
- `Server`: Web server software and version (e.g., `Apache/2.4.54`, `nginx/1.20.1`)
- `X-Powered-By`: Server-side technology (e.g., `PHP/8.1.0`, `ASP.NET`)
- `X-Framework`: Application framework (e.g., `WordPress/6.2.0`); *Note: This is a custom header set in this lab for training purposes. Most real-world applications do not expose a standard `X-Framework` header. In practice, rely on meta tags, URL patterns, and tools like Wappalyzer for framework identification.*
- `X-Generator`: CMS or framework generator (e.g., `WordPress 6.2.0`)
- `X-AspNet-Version`: ASP.NET version (if using ASP.NET)

**Expected findings:**
```
Server: Apache/2.4.54
X-Powered-By: PHP/8.1.0
X-Framework: WordPress/6.2.0
```

**What this tells us:**
- Web server: Apache version 2.4.54
- Programming language: PHP version 8.1.0
- CMS/Framework: WordPress version 6.2.0

**Troubleshooting:**
- If headers don't show technology info, check HTML source
- Some servers hide version information for security
- Try different endpoints: `curl -I http://target.lab/index.php`

### Step 4: Use Browser DevTools

Open the website in a browser and use Developer Tools to inspect the page source and network traffic.

**Detailed Steps:**

1. **Open the website in browser:**
   - Navigate to: `http://target.lab`

2. **Open Developer Tools:**
   - Press `F12` key
   - Or right-click on the page → Select "Inspect" or "Inspect Element"
   - Or use menu: View → Developer → Developer Tools (Chrome/Edge)
   - Or use menu: Tools → Web Developer → Inspector (Firefox)

3. **Check Network Tab for response headers:**
   - Click on the **Network** tab
   - Refresh the page (F5)
   - Click on the main request (usually `target.lab` or `index.html`)
   - Click on **Headers** tab
   - Scroll to **Response Headers** section
   - Look for technology-related headers

   **Expected headers in Network tab:**
   ```
   Server: Apache/2.4.54
   X-Powered-By: PHP/8.1.0
   X-Framework: WordPress/6.2.0
   ```

4. **Check Elements Tab for HTML source:**
   - Click on the **Elements** tab (or **Inspector** in Firefox)
   - Look at the HTML source code
   - Press `Ctrl+F` (or `Cmd+F` on Mac) to search

5. **Search for meta tags:**
   - Search for: `generator`
   - Look for: `<meta name="generator" content="WordPress 6.2.0">`

6. **Look for framework-specific paths:**
   - Search for: `wp-content`, `wp-admin`, `wp-includes`
   - These indicate WordPress is being used

7. **Check Sources Tab for framework files:**
   - Click on the **Sources** tab
   - Look for framework-specific directories:
     - `/wp-content/` - WordPress content
     - `/wp-includes/` - WordPress core files
     - `/wp-admin/` - WordPress admin files

**Look for:**
- **Meta tags**: `<meta name="generator" content="WordPress 6.2.0">`
- **CSS/JS paths**: `/wp-content/`, `/wp-admin/`, `/wp-includes/`
- **Script sources**: Check `<script src="...">` tags for framework files
- **Link tags**: Check `<link rel="stylesheet" href="...">` for framework CSS

**Example findings:**
```html
<meta name="generator" content="WordPress 6.2.0" />
<link rel='stylesheet' href='/wp-content/themes/twenty-twenty-three/style.css' />
<script src='/wp-includes/js/jquery/jquery.min.js'></script>
```

**What this confirms:**
- WordPress version: 6.2.0
- WordPress theme: twenty-twenty-three
- Using jQuery library

### Step 5: Use Wappalyzer (Browser Extension)

Wappalyzer is a browser extension that automatically detects technologies on websites.

**Detailed Steps:**

1. **Install Wappalyzer extension:**
   - **Chrome/Edge**: Visit https://chrome.google.com/webstore → Search "Wappalyzer" → Click "Add to Chrome"
   - **Firefox**: Visit https://addons.mozilla.org → Search "Wappalyzer" → Click "Add to Firefox"
   - Follow the installation prompts

2. **Verify installation:**
   - You should see the Wappalyzer icon in your browser toolbar
   - The icon shows a "W" or technology stack icon

3. **Visit the target website:**
   - Navigate to: `http://target.lab`
   - Wait for the page to fully load

4. **View detected technologies:**
   - **Method 1**: Click the Wappalyzer icon in the toolbar
   - **Method 2**: The icon may show a badge with the number of technologies detected
   - A popup or sidebar will show all detected technologies

5. **Review the technology list:**
   - Technologies are organized by category (CMS, Web Servers, Programming Languages, etc.)
   - Each technology shows its name and version (if detected)

**Expected detections:**
- **CMS**: WordPress 6.2.0
- **Programming Languages**: PHP 8.1.0
- **Web Servers**: Apache 2.4.54
- **JavaScript Libraries**: jQuery (if present)

**Wappalyzer output example:**
```
CMS
  WordPress 6.2.0

Web Servers
  Apache 2.4.54

Programming Languages
  PHP 8.1.0
```

**Troubleshooting:**
- If Wappalyzer doesn't detect technologies, refresh the page
- Some technologies may not be detected if they're hidden
- Check browser console for any errors
- Try disabling other extensions that might interfere

### Step 6: Check Common Files and Directories

Look for framework-specific files and directories that reveal technology information.

**Detailed Steps:**

1. **Check for WordPress readme file:**
   ```bash
   curl http://target.lab/readme.html
   ```

   **Expected output:**
   ```
   <html>
   <head><title>WordPress Readme</title></head>
   <body>
   <h1>WordPress Version: 6.2.0</h1>
   <p>PHP Version: 8.1.0</p>
   <p>Apache Version: 2.4.54</p>
   </body>
   </html>
   ```

   **What this reveals:**
   - WordPress version: 6.2.0
   - PHP version: 8.1.0
   - Apache version: 2.4.54

2. **Check for WordPress admin directory:**
   ```bash
   curl -I http://target.lab/wp-admin/
   ```

   **Expected output:**
   ```
   HTTP/1.1 301 Moved Permanently
   Location: http://target.lab/wp-admin/
   ```

   Or:
   ```
   HTTP/1.1 200 OK
   ```

   **What this confirms:**
   - WordPress is installed (wp-admin directory exists)
   - Admin panel is accessible (or redirected)

3. **Check for WordPress includes directory:**
   ```bash
   curl -I http://target.lab/wp-includes/
   ```

   **Expected output:**
   ```
   HTTP/1.1 403 Forbidden
   ```

   **What this means:**
   - Directory exists but access is forbidden (normal for wp-includes)
   - Confirms WordPress installation

4. **Check robots.txt file:**
   ```bash
   curl http://target.lab/robots.txt
   ```

   **Expected output:**
   ```
   User-agent: *
   Disallow: /wp-admin/
   Disallow: /wp-includes/
   ```

   **What this reveals:**
   - Confirms WordPress directories
   - May reveal additional hidden directories

5. **Check for .htaccess file (Apache configuration):**
   ```bash
   curl http://target.lab/.htaccess
   ```

   **Expected output:**
   ```
   # BEGIN WordPress
   <IfModule mod_rewrite.c>
   RewriteEngine On
   RewriteBase /
   RewriteRule ^index\.php$ - [L]
   RewriteCond %{REQUEST_FILENAME} !-f
   RewriteCond %{REQUEST_FILENAME} !-d
   RewriteRule . /index.php [L]
   </IfModule>
   # END WordPress
   ```

   **What this confirms:**
   - Apache web server (uses .htaccess)
   - WordPress rewrite rules
   - WordPress is configured

**Key findings summary:**
- `/readme.html` - Contains version information
- `/robots.txt` - Reveals directory structure and confirms WordPress
- `/wp-admin/` - WordPress admin directory (confirms WordPress)
- `/wp-includes/` - WordPress core files directory
- `/.htaccess` - Apache configuration file (confirms Apache)

**Troubleshooting:**
- If files return 404, they may not exist or be hidden
- Some servers hide version files for security
- Try different file names: `readme.txt`, `README.html`, `version.txt`

### Step 7: Analyze robots.txt

The robots.txt file often reveals technology and directory structure.

**Detailed Steps:**

1. **Retrieve robots.txt:**
   ```bash
   curl http://target.lab/robots.txt
   ```

2. **Expected output:**
   ```
   User-agent: *
   Disallow: /wp-admin/
   Disallow: /wp-includes/
   Disallow: /wp-content/plugins/
   Disallow: /wp-content/themes/
   ```

   **What this reveals:**
   - WordPress directories are listed
   - Confirms WordPress is being used
   - May reveal plugin and theme directories

3. **Analyze the content:**
   - `Disallow: /wp-admin/` - WordPress admin directory
   - `Disallow: /wp-includes/` - WordPress core files
   - `Disallow: /wp-content/plugins/` - WordPress plugins
   - `Disallow: /wp-content/themes/` - WordPress themes

**This confirms WordPress is being used.**

### Step 8: Check Version Files

Many applications have version files that explicitly state the software version.

**Detailed Steps:**

1. **Check readme.html:**
   ```bash
   curl http://target.lab/readme.html
   ```

2. **Expected output:**
   ```
   <html>
   <head><title>WordPress Readme</title></head>
   <body>
   <h1>Welcome to WordPress</h1>
   <p>WordPress Version: 6.2.0</p>
   <p>PHP Version: 8.1.0</p>
   <p>Apache Version: 2.4.54</p>
   <p>MySQL Version: 8.0.33</p>
   </body>
   </html>
   ```

3. **Alternative version files to check:**
   ```bash
   curl http://target.lab/version.txt
   curl http://target.lab/VERSION
   curl http://target.lab/CHANGELOG.txt
   ```

4. **Check WordPress version in source:**
   ```bash
   curl http://target.lab | grep -i "wordpress\|version"
   ```

**Key version information:**
- WordPress Version: 6.2.0
- PHP Version: 8.1.0
- Apache Version: 2.4.54
- MySQL Version: 8.0.33 (if shown)

**What this enables:**
- Search for known vulnerabilities in WordPress 6.2.0
- Identify PHP-specific attack vectors
- Understand server configuration

### Step 9: Retrieve Flag

Based on the technology identification (WordPress), check the WordPress admin directory for the flag.

**Detailed Steps:**

1. **Check WordPress admin directory for flag:**
   ```bash
   curl http://target.lab/wp-admin/flag.txt
   ```

2. **Expected output:**
   ```
   OCR{t3ch_1d3nt1f1c4t10n_b4s1c}
   ```

3. **Alternative locations to check:**
   ```bash
   # Check root directory
   curl http://target.lab/flag.txt
   
   # Check wp-content
   curl http://target.lab/wp-content/flag.txt
   
   # Check wp-includes
   curl http://target.lab/wp-includes/flag.txt
   ```

4. **If flag is not directly accessible, try directory listing:**
   ```bash
   curl http://target.lab/wp-admin/
   ```
   
   Look for links to flag.txt in the HTML response.

**Flag:**
```
OCR{t3ch_1d3nt1f1c4t10n_b4s1c}
```

**Troubleshooting:**
- If you get 404, try different paths: `/wp-admin/flag`, `/flag.txt`, `/FLAG.txt`
- Check if directory listing is enabled: `curl http://target.lab/wp-admin/`
- Use browser to navigate to the directory and look for the file

### Step 10: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{t3ch_1d3nt1f1c4t10n_b4s1c}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Successfully added hostname to /etc/hosts
- ✅ Accessed web server and retrieved initial headers
- ✅ Analyzed HTTP headers and identified technologies
- ✅ Used browser DevTools to inspect HTML source
- ✅ Used Wappalyzer to detect technologies
- ✅ Checked common files and directories (readme.html, robots.txt, wp-admin)
- ✅ Confirmed WordPress 6.2.0, PHP 8.1.0, Apache 2.4.54
- ✅ Retrieved flag from wp-admin directory
- ✅ Verified flag format is correct: `OCR{...}`

## Alternative Tools

### WhatWeb
```bash
whatweb http://target.lab
```

### BuiltWith (Online Tool)
- Visit: https://builtwith.com
- Enter target URL
- View technology stack

### Netcraft (Online Tool)
- Visit: https://sitereport.netcraft.com
- Enter target URL
- View server and technology information

### Manual Header Analysis
```bash
# Full request/response
curl -v http://target.lab

# Just headers
curl -I http://target.lab

# Save headers to file
curl -I http://target.lab > headers.txt
```

## Common Technology Indicators

### Web Servers
- **Apache**: `Server: Apache/X.X.X`
- **Nginx**: `Server: nginx/X.X.X`
- **IIS**: `Server: Microsoft-IIS/X.X`

### Programming Languages
- **PHP**: `X-Powered-By: PHP/X.X.X`
- **ASP.NET**: `X-Powered-By: ASP.NET`
- **Python**: Check for `/wsgi.py`, `/app.py`
- **Node.js**: Check for `package.json`, `/node_modules/`

### CMS Platforms
- **WordPress**: `/wp-admin/`, `/wp-content/`, `/wp-includes/`
- **Drupal**: `/sites/`, `/modules/`, `/themes/`
- **Joomla**: `/administrator/`, `/components/`

### Frameworks
- **Laravel**: `/vendor/`, `X-Powered-By: Laravel`
- **Django**: `/admin/`, `/static/`
- **Rails**: `/assets/`, `X-Runtime: Ruby`

## Hints

1. Start by examining HTTP response headers
2. Use browser DevTools to inspect page source
3. Look for meta tags in HTML source
4. Check for framework-specific directories
5. Use Wappalyzer browser extension for quick identification
6. Check robots.txt for directory hints
7. Look for version files (readme.html, version.txt, etc.)
8. Flag is in the WordPress admin directory

## Common Mistakes

- Not checking HTTP headers thoroughly
- Missing meta tags in HTML source
- Not using browser DevTools
- Forgetting to check robots.txt
- Not looking for version files
- Assuming technologies without verification
- Not checking multiple sources (headers, HTML, files)

## Educational Context

### Why Technology Identification Matters

- **Vulnerability Research**: Known technologies have known vulnerabilities
- **Tool Selection**: Different tools work better with different technologies
- **Attack Planning**: Understanding the stack helps plan attacks
- **Defense**: Helps identify what needs patching

### Information Sources

1. **HTTP Headers**: Server, X-Powered-By, custom headers
2. **HTML Source**: Meta tags, script sources, CSS links
3. **File Structure**: Framework-specific directories
4. **Error Messages**: Often reveal technology versions
5. **Cookies**: Framework-specific cookie names
6. **URL Patterns**: Framework routing patterns

### Security Implications

- **Version Disclosure**: Reveals potentially vulnerable versions
- **Attack Surface**: Different technologies = different attack vectors
- **Exploit Selection**: Choose exploits based on identified technologies
- **Defense Evasion**: Some technologies have specific bypass techniques

## Further Reading

- OWASP: Information Gathering
- Wappalyzer: https://www.wappalyzer.com
- WhatWeb: https://github.com/urbanadventurer/WhatWeb
- BuiltWith: https://builtwith.com

