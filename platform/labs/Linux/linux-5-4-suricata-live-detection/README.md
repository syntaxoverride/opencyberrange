# Sentinel Defense Corp: Live IDS Detection

## Overview

Students act as a SOC analyst investigating an active cyberattack against a corporate DMZ. An automated attacker is sending SQL injection and command injection payloads to hosts on the network every 10 seconds. The student must use Suricata IDS to detect the attacks in real-time by writing custom detection rules, then extract indicators of compromise from the captured payloads.

This is the first lab in the curriculum that uses **live traffic**: the attack is happening continuously, not replayed from a PCAP.

## Architecture

```
┌──────────────┐     SQLi GET / CMDi POST      ┌──────────────┐
│   attacker   │ ────────────────────────────▶  │   analyst    │
│  (auto scan) │           every 10s            │ (IDS sensor) │
└──────┬───────┘                                └──────────────┘
       │                                         Student SSHs here
       │          Recon GET requests             ┌──────────────┐
       └────────────────────────────────────▶   │    target     │
                  (distinctive User-Agent)       │ (web portal)  │
                                                 └──────────────┘
                                                  Student SSHs here
                                                  to check access logs
```

**Flag parts:**
- Part 1: Extracted from Suricata alert payload (SQLi campaign tag)
- Part 2: Extracted from Suricata alert payload (CMDi exfil tag)
- Part 3: Found in target's nginx access log (attacker User-Agent)

## Solution Walkthrough

### Step 1: Connect to the IDS Sensor

```bash
ssh analyst@<analyst_ip>
# Password: S3nt1n3l_S0C#
```

### Step 2: Observe Attack Traffic

```bash
sudo tcpdump -i eth0 -A -c 20 port 80
```

You'll see HTTP requests arriving every few seconds. Look for:
- GET requests with `UNION SELECT` in the URL (SQL injection)
- POST requests with `cat /etc` in the body (command injection)
- Note the URL parameters: `campaign=` and `exfil=`

### Step 3: Write Suricata Detection Rules

```bash
cat > /etc/suricata/rules/local.rules << 'EOF'
alert http any any -> any any (msg:"SQLi Attack Detected"; content:"UNION SELECT"; nocase; http_uri; sid:1000001; rev:1;)
alert http any any -> any any (msg:"Command Injection Detected"; content:"cat /etc"; nocase; http_client_body; sid:1000002; rev:1;)
EOF
```

### Step 4: Reload Suricata Rules

```bash
sudo kill -USR2 $(pgrep suricata)
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
# Part 1: campaign tag from SQLi alert
jq -r 'select(.alert != null) | select(.alert.signature_id == 1000001) | .http.url' \
    /var/log/suricata/eve.json | grep -oP 'campaign=\K[^&]+' | head -1
# → d3t3ct

# Part 2: exfil tag from CMDi alert
jq -r 'select(.alert != null) | select(.alert.signature_id == 1000002) | .payload_printable' \
    /var/log/suricata/eve.json | grep -oP 'exfil=\K[^& \\]+' | head -1
# → rul3
```

Or use the built-in validator: `validate-flag`

### Step 7: Get Flag Part 3 from Target

```bash
ssh webadmin@<target_ip>
# Password: Dmz_Adm1n_2024#

grep "SentinelBreaker" /var/log/nginx/access.log | head -1
# Look for User-Agent: SentinelBreaker/wr1t3r
# Part 3: wr1t3r
```

### Step 8: Assemble Flag

```
OCR{d3t3ct_rul3_wr1t3r}
```

## Common Mistakes

- **Not waiting long enough after rule reload.** The attacker sends requests every ~10 seconds. Wait at least 15-20 seconds after reloading rules before checking alerts.
- **Wrong content modifier.** `http_uri` matches GET parameters. `http_client_body` matches POST bodies. Using the wrong one means no match.
- **Forgetting `nocase`.** The content match is case-sensitive by default. Use `nocase` for reliability.
- **Looking for the flag in the wrong place.** Parts 1 and 2 come from Suricata alerts (analyst box). Part 3 comes from the target's nginx access log (target box).
- **Not using `jq` properly.** Each line in eve.json is a separate JSON object. Use `jq 'select(.alert != null)'` to filter only alert events.

## Technical Details

- **IDS Engine:** Suricata 6.0 (af-packet capture on eth0)
- **Attack Tool:** Custom curl-based scanner running in a loop
- **Attack Vectors:** UNION-based SQL injection (GET), OS command injection (POST)
- **Detection Method:** Content matching on HTTP URI and request body
- **Payload Capture:** eve.json with `payload-printable` and `http-body-printable` enabled

## Defensive Recommendations

- Deploy IDS/IPS at network boundaries with tuned rule sets
- Use `payload-printable` in Suricata for forensic analysis of alerts
- Monitor for automated scanning patterns (regular intervals, consistent User-Agent)
- Correlate IDS alerts with web server access logs for full attack visibility
- Block known-bad User-Agent strings at the WAF layer
