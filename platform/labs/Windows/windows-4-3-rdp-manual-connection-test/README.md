# Lab 4.3: RDP Manual Connection Test

## Learning Objectives
- Attempt RDP connection with known credentials
- Understand RDP client usage
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

3. **Verify RDP service is running:**
   ```bash
   nmap -p 3389 <target_ip>
   ```

   **Expected output:**
   ```
   PORT     STATE SERVICE
   3389/tcp open  ms-wbt-server
   ```

### Step 2: Connect via RDP

Connect to the target using RDP client with provided credentials.

**Detailed Steps:**

1. **Verify RDP client is installed:**
   ```bash
   which xfreerdp
   # Or
   which rdesktop
   ```

2. **Connect using xfreerdp:**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `xfreerdp /v:<target_ip> /u:admin /p:password`)

   **Command breakdown:**
   - `xfreerdp`: FreeRDP client for RDP connections
   - `/v:<target_ip>`: Target IP address
   - `/u:admin`: Username for authentication
   - `/p:password`: Password for authentication

3. **Expected connection process:**
   - RDP client window will open
   - Connection will be established
   - You'll see the Linux desktop (xfce4)
   - You're logged in as admin

4. **Alternative: Connect with rdesktop:**
   ```bash
   rdesktop <target_ip> -u admin -p password
   ```

5. **Alternative: Connect with certificate ignore (if needed):**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password /cert:ignore
   ```

**Troubleshooting:**
- **"Connection refused"**: Verify IP and port 3389
- **"Authentication failed"**: Check username (admin) and password (password)
- **"Certificate error"**: Use `/cert:ignore` flag
- **Connection timeout**: Check firewall or network connectivity

### Step 3: Navigate to Flag

Once connected via RDP, locate and view the flag file.

**Detailed Steps:**

1. **After successful RDP connection:**
   - You should see the Linux desktop (xfce4)
   - You're logged in as `admin`

2. **Method 1: Using Terminal:**
   - Right-click the desktop and select "Open Terminal Here"
   - Or open a terminal from the applications menu
   - Navigate to flag location:
     ```bash
     cd /home/admin
     ls flag.txt
     cat flag.txt
     ```

3. **Method 2: Using file manager:**
   - Click the File Manager icon in the taskbar to open file manager
   - Navigate to: `/home/admin/`
   - Look for `flag.txt`
   - Double-click to open in a text editor

4. **Method 3: Using Terminal:**
   - Open a terminal from the applications menu
   - Navigate and view:
     ```bash
     cd /home/admin
     cat flag.txt
     ```

5. **Alternative locations to check:**
   ```bash
   cat /home\flag.txt
   cat /home\Users\admin\Desktop\flag.txt
   cat /home\Users\admin\Documents\flag.txt
   ```

6. **Expected flag content:**
   ```
   OCR{rdp_m4nu4l_c0nn3ct}
   ```

7. **Copy flag to clipboard:**
   - Select the flag text
   - Press `Ctrl+C` to copy
   - Paste into your notes

### Step 4: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{rdp_m4nu4l_c0nn3ct}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters
- ✅ Copied correctly from RDP session

**Success Criteria:**
- ✅ Verified target IP and RDP service accessibility
- ✅ Successfully connected via RDP using xfreerdp
- ✅ Logged in with credentials (admin/password)
- ✅ Navigated to flag location (/home/admin/flag.txt)
- ✅ Viewed flag content using terminal, file manager, 
- ✅ Copied flag to clipboard or notes
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- RDP allows remote desktop access (xrdp enables this on Linux systems)
- xfreerdp is a common Linux RDP client
- Understanding RDP connection process is essential
- Multiple methods exist to access files in Linux
- Manual connection testing verifies credentials work

## Common Mistakes
- Incorrect xfreerdp syntax
- Wrong credentials
- Not navigating to flag location

## Hints
1. Username: admin
2. Password: password
3. Use xfreerdp client
4. Flag in /home/admin/flag.txt