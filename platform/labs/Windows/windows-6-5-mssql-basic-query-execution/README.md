# Lab 6.5: MS-SQL Basic Query Execution
## Learning Objectives
- Execute SQL queries via authenticated session
- Understand database navigation
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

### Step 3: Execute Queries

Execute SQL queries to explore the database and locate the flag.

**Detailed Steps:**

1. **List all databases:**
   ```sql
   SHOW DATABASES;
   ```

   **Expected output:**
   ```
   +--------------------+
   | Database           |
   +--------------------+
   | information_schema |
   | mysql              |
   | performance_schema |
   | testdb             |
   +--------------------+
   4 rows in set (0.00 sec)
   ```

2. **Select the testdb database:**
   ```sql
   USE testdb;
   ```

   **Expected output:**
   ```
   Database changed
   ```

3. **List tables in testdb:**
   ```sql
   SHOW TABLES;
   ```

   **Expected output:**
   ```
   +------------------+
   | Tables_in_testdb  |
   +------------------+
   | flags             |
   | users             |
   +------------------+
   2 rows in set (0.00 sec)
   ```

4. **Query the flags table:**
   ```sql
   SELECT * FROM flags;
   ```

   **Expected output:**
   ```
   +----+------------------------------------------+
   | id | flag                                     |
   +----+------------------------------------------+
   |  1 | OCR{mssql_qu3ry}      |
   +----+------------------------------------------+
   1 row in set (0.00 sec)
   ```

5. **Alternative: Query specific columns:**
   ```sql
   SELECT flag FROM flags;
   ```

6. **Alternative: Query with WHERE clause:**
   ```sql
   SELECT * FROM flags WHERE id=1;
   ```

### Step 4: Retrieve Flag

Extract the flag from the query results.

**Detailed Steps:**

1. **The flag is in the query output:**
   ```
   OCR{mssql_qu3ry}
   ```

2. **Copy the flag:**
   - Select the flag text from the query output
   - Copy to your notes

3. **Exit MySQL client:**
   ```sql
   exit
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{mssql_qu3ry}
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
- ✅ Listed databases using SHOW DATABASES
- ✅ Selected testdb database using USE command
- ✅ Listed tables using SHOW TABLES
- ✅ Queried flags table using SELECT
- ✅ Retrieved flag from query results
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- SQL queries allow data retrieval from databases
- Understanding database structure (databases, tables, columns) is essential
- SHOW commands help explore database structure
- SELECT queries retrieve data from tables
- Database navigation skills are crucial for database security testing
## Hints
1. Connect with sa:password
2. Use testdb database
3. Query flags table