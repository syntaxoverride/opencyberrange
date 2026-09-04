# Aegis Security Corp: Brute Force Detection

## Overview

Students act as a SOC analyst investigating an active brute-force credential stuffing attack against a corporate authentication portal. An automated attacker is sending HTTP POST login requests every 3 seconds with different username/password combinations. The student must use Suricata IDS to detect the attacks in real-time by writing custom detection rules, then extract indicators of compromise from the captured payloads and the target's web server logs.

This lab focuses on **brute-force detection**: identifying high-frequency login attempts, campaign tracking markers, and attacker tool signatures.

## Architecture

```
                     HTTP POST /login (every 3s)
┌──────────────┐    username/password combos        ┌──────────────┐
│   attacker   │ ──────────────────────────────────▶ │    sensor    │
│ (brute-force)│                                     │ (IDS sensor) │
└──────┬───────┘                                     └──────────────┘
       │                                              Student SSHs here
       │          Recon GET requests                  ┌──────────────┐
       └─────────────────────────────────────────▶   │    target    │
                  (AegisCracker User-Agent)           │ (web portal) │
                                                      └──────────────┘
                                                       Student SSHs here
                                                       to check access logs
```

**Flag parts:**
- Part 1: Extracted from Suricata alert payload (campaign marker in successful login)
- Part 2: Extracted from Suricata alert payload (exfil tag in failed login attempts)
- Part 3: Found in target's nginx access log (attacker User-Agent string)

## Solution Walkthrough

### Step 1: Connect to the IDS Sensor

```bash
ssh analyst@<sensor_ip>
# Password: A3g1s_S0C_2024#
```

### Step 2: Observe Attack Traffic

```bash
sudo tcpdump -i eth0 -A -c 20 port 80
```

You'll see HTTP POST requests arriving every few seconds targeting /login. Look for:
- POST bodies with `username=` and `password=` fields (brute-force attempts)
- Most responses contain `login_failed`
- Some contain `login_success` with a `campaign=` parameter
- Failed attempts include an `exfil=` parameter

### Step 3: Write Suricata Detection Rules

```bash
cat > /etc/suricata/rules/local.rules << 'EOF'
alert http any any -> any any (msg:"Brute Force Login Attempt"; flow:to_server,established; content:"POST"; http_method; content:"password"; http_client_body; sid:1000001; rev:1;)
alert http any any -> any any (msg:"Campaign Marker Detected"; flow:to_server,established; content:"POST"; http_method; content:"campaign=brut3"; http_client_body; sid:1000002; rev:1;)
EOF
```

### Step 4: Reload Suricata Rules

```bash
sudo kill -USR2 $(pgrep -x Suricata-Main)
```

### Step 5: Wait and Check Alerts

Wait 15-20 seconds for the next attack cycle, then check:

```bash
# Quick check
cat /var/log/suricata/fast.log

# Detailed JSON alerts
jq 'select(.alert != null)' /var/log/suricata/eve.json
```

### Step 6: Extract Flag Parts 1 and 2

```bash
# Part 1: campaign tag from successful login alert
jq -r 'select(.alert != null) | select(.alert.signature_id == 1000002) | .payload_printable' \
    /var/log/suricata/eve.json | grep -oP 'campaign=\K[^& \\]+' | head -1
# → brut3

# Part 2: exfil tag from brute-force alert
jq -r 'select(.alert != null) | select(.alert.signature_id == 1000001) | .payload_printable' \
    /var/log/suricata/eve.json | grep -oP 'exfil=\K[^& \\]+' | head -1
# → d3t3ct
```

### Step 7: Get Flag Part 3 from Target

```bash
ssh webadmin@<target_ip>
# Password: A3g1s_Adm1n#

grep "AegisCracker" /var/log/nginx/access.log | head -1
# Look for User-Agent: AegisCracker/bl0ck
# Part 3: bl0ck
```

### Step 8: Assemble Flag

```
OCR{brut3_d3t3ct_bl0ck}
```

## Common Mistakes

- **Not waiting long enough after rule reload.** The attacker sends requests every ~3 seconds. Wait at least 15-20 seconds after reloading rules before checking alerts.
- **Wrong content modifier.** `http_client_body` matches POST request bodies. Using `http_uri` won't match POST data.
- **Missing `http_method` match.** Without matching on `POST`, the rule may fire on unrelated HTTP traffic.
- **Looking for the flag in the wrong place.** Parts 1 and 2 come from Suricata alerts (sensor box). Part 3 comes from the target's nginx access log (target box).
- **Not using `jq` properly.** Each line in eve.json is a separate JSON object. Use `jq 'select(.alert != null)'` to filter only alert events.

## Technical Details

- **IDS Engine:** Suricata 6.0 (af-packet capture on eth0)
- **Attack Tool:** Custom curl-based brute-force script running in a loop
- **Attack Vector:** HTTP POST credential stuffing with embedded campaign/exfil tracking tags
- **Detection Method:** Content matching on HTTP method and request body
- **Payload Capture:** eve.json with `payload-printable` and `http-body-printable` enabled

## Defensive Recommendations

- Deploy IDS/IPS rules to detect high-frequency login attempts from single sources
- Implement rate limiting on authentication endpoints
- Use `payload-printable` in Suricata for forensic analysis of alert payloads
- Monitor for automated scanning patterns (regular intervals, consistent User-Agent)
- Correlate IDS alerts with web server access logs for full attack visibility
- Block known-bad User-Agent strings at the WAF layer
- Implement account lockout policies after repeated failed login attempts
