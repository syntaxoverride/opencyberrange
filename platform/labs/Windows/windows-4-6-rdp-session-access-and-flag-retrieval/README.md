# Lab 4.6: RDP Session Access and Flag Retrieval

## Learning Objectives
- Connect via RDP, navigate system, find flag
- Understand RDP session management
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

### Step 2: Connect via RDP

Connect to the target using RDP client with provided credentials.

**Detailed Steps:**

1. **Verify RDP client is installed:**
   ```bash
   which xfreerdp
   ```

2. **Connect using xfreerdp:**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password123
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `xfreerdp /v:<target_ip> /u:admin /p:password123`)

   **Command breakdown:**
   - `xfreerdp`: FreeRDP client for RDP connections
   - `/v:<target_ip>`: Target IP address
   - `/u:admin`: Username for authentication
   - `/p:password123`: Password for authentication

3. **Expected connection:**
   - RDP client window opens
   - Linux desktop (xfce4) appears
   - You're logged in as admin

4. **Alternative: Connect with certificate ignore (if needed):**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password123 /cert:ignore
   ```

### Step 3: Navigate Desktop

Locate the flag file on the Linux desktop (xfce4).

**Detailed Steps:**

1. **After successful RDP connection:**
   - You should see the Linux desktop (xfce4)
   - Look for `flag.txt` file icon on the desktop

2. **Method 1: Using Desktop (GUI):**
   - Look for `flag.txt` icon on the desktop
   - Double-click to open in a text editor
   - Copy the flag content

3. **Method 2: Using Terminal:**
   - Right-click the desktop and select "Open Terminal Here"
   - Or open a terminal from the applications menu
   - Navigate to desktop:
     ```bash
     cd /home/admin/Desktop
     ls flag.txt
     cat flag.txt
     ```

4. **Method 3: Using Terminal:**
   - Open a terminal from the applications menu
   - Navigate and view:
     ```bash
     cd /home/admin/Desktop
     cat flag.txt
     ```

5. **Method 4: Direct path:**
   ```bash
   cat /home\Users\admin\Desktop\flag.txt
   ```

6. **If flag is not on desktop, check other locations:**
   ```bash
   cat /home\Users\admin\flag.txt
   cat /home\flag.txt
   ls /home\Users\admin\Desktop
   ```

### Step 4: Retrieve Flag

Extract and copy the flag from the desktop.

**Detailed Steps:**

1. **View flag content:**
   - Using text editor: Double-click `flag.txt` on desktop
   - Using Terminal: `cat /home\Users\admin\Desktop\flag.txt`
   - Using Terminal: `cat /home/admin/Desktop/flag.txt`

2. **Expected flag content:**
   ```
   OCR{rdp_s3ss10n_4cc3ss}
   ```

3. **Copy flag to clipboard:**
   - Select the flag text
   - Press `Ctrl+C` to copy
   - Paste into your notes

4. **Alternative: Save flag to file (if needed):**
   ```bash
   cat /home\Users\admin\Desktop\flag.txt > /home/admin/flag_copy.txt
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{rdp_s3ss10n_4cc3ss}
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
- ✅ Logged in with credentials (admin/password123)
- ✅ Navigated to desktop location
- ✅ Located flag.txt on desktop
- ✅ Retrieved flag content using text editor or terminal
- ✅ Copied flag to clipboard or notes
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- RDP provides full desktop access (xrdp enables this on Linux systems)
- Understanding Linux file system paths is essential
- Multiple methods exist to access files (GUI, terminal)
- Desktop is a common location for files in Linux
- Session management includes file access and navigation

## Common Mistakes
- Not navigating properly
- Missing desktop location
- Not using terminal

## Hints
1. Connect with admin:password123
2. Flag is on desktop
3. Use terminal to view