#!/usr/bin/env python3
"""
Generate realistic DNS query logs with normal traffic and malicious C2 communication.
"""

import random
import string
from datetime import datetime, timedelta

# Configuration
NORMAL_IPS = [
    "10.50.1.15",   # Doctor's workstation
    "10.50.1.22",   # Nurse station
    "10.50.2.8",    # Medical records system
    "10.50.2.45",   # Pharmacy system
    "10.50.3.12",   # Lab system
    "10.50.1.33",   # Admin workstation
]

INFECTED_IP = "10.50.4.67"  # Radiology workstation (infected)

# Normal domains that a hospital would query
NORMAL_DOMAINS = [
    ("google.com", "142.250.80.46"),
    ("microsoft.com", "20.112.52.29"),
    ("office365.com", "52.97.148.194"),
    ("windows.com", "40.112.72.205"),
    ("azure.com", "13.107.21.200"),
    ("medicareportal.gov", "52.222.146.78"),
    ("ehr-system.net", "198.51.100.45"),
    ("pharmacy-db.com", "203.0.113.89"),
    ("lab-results.org", "198.51.100.123"),
    ("radiology-pacs.com", "203.0.113.200"),
    ("amazonaws.com", "54.239.28.85"),
    ("cloudflare.com", "104.16.132.229"),
]

# Malicious C2 domain - flag embedded in domain name pattern
C2_BASE_DOMAIN = "c2-dns-3xf1ltr4t10n.tk"
C2_SERVER_IP = "185.220.101.47"  # Suspicious IP

def generate_timestamp(base_time, offset_seconds):
    """Generate a timestamp with offset."""
    dt = base_time + timedelta(seconds=offset_seconds)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def generate_random_subdomain(length=16):
    """Generate a random subdomain (simulating data exfiltration)."""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_normal_traffic(base_time, count=120):
    """Generate normal hospital DNS traffic."""
    logs = []
    time_offset = 0

    for i in range(count):
        src_ip = random.choice(NORMAL_IPS)
        domain, ip = random.choice(NORMAL_DOMAINS)
        query_type = "A" if random.random() > 0.1 else "AAAA"
        timestamp = generate_timestamp(base_time, time_offset)
        time_offset += random.randint(5, 30)  # 5-30 seconds between normal queries

        log = f"{timestamp} {src_ip} {query_type} {domain} -> {ip}"
        logs.append(log)

    return logs

def generate_c2_traffic(base_time, start_offset=1800, count=45):
    """Generate malicious C2 DNS traffic with data exfiltration pattern."""
    logs = []
    timestamp_base = base_time + timedelta(seconds=start_offset)

    # Add a comment line indicating start of suspicious activity
    scan_start = generate_timestamp(base_time, start_offset)
    logs.append(f"# {scan_start} NOTICE: High-frequency DNS queries detected from {INFECTED_IP}")

    # Generate C2 queries with random subdomains (data exfiltration pattern)
    for i in range(count):
        # Random subdomain simulates data being exfiltrated
        random_subdomain = generate_random_subdomain(random.randint(12, 24))
        full_domain = f"{random_subdomain}.{C2_BASE_DOMAIN}"

        timestamp = generate_timestamp(timestamp_base, i * random.randint(8, 15))
        query_type = "A"

        log = f"{timestamp} {INFECTED_IP} {query_type} {full_domain} -> {C2_SERVER_IP}"
        logs.append(log)

    # Add analysis comment with flag
    scan_end = generate_timestamp(timestamp_base, count * 15 + 30)
    logs.append(f"# {scan_end} ANALYSIS: Malware C2 detected - Source: {INFECTED_IP}, Domain: {C2_BASE_DOMAIN}, Pattern: Data exfiltration via DNS")
    logs.append(f"# {scan_end} ALERT: Malicious domain pattern contains flag: OCR{{dns_3xf1ltr4t10n}}")

    return logs

def generate_more_normal_traffic(base_time, count=60):
    """Generate additional normal traffic mixed with C2."""
    logs = []
    time_offset = 0

    for i in range(count):
        src_ip = random.choice(NORMAL_IPS)
        domain, ip = random.choice(NORMAL_DOMAINS)
        query_type = "A" if random.random() > 0.15 else "AAAA"
        timestamp = generate_timestamp(base_time, time_offset)
        time_offset += random.randint(10, 40)

        log = f"{timestamp} {src_ip} {query_type} {domain} -> {ip}"
        logs.append(log)

    return logs

def main():
    """Generate complete DNS query log file."""
    base_time = datetime(2024, 1, 4, 14, 0, 0)  # Start at 2 PM

    # Generate logs
    print("# MediCare Regional Hospital - DNS Query Logs")
    print("# Format: TIMESTAMP SOURCE_IP QUERY_TYPE DOMAIN -> IP_ADDRESS")
    print("# DNS Server: 10.10.3.10")
    print("#")

    # Interleave normal and malicious traffic to make it more realistic
    all_logs = []

    # Normal traffic before infection becomes active
    normal_before = generate_normal_traffic(base_time, count=50)
    all_logs.extend(normal_before)

    # C2 traffic starts (malware becomes active)
    c2_traffic = generate_c2_traffic(base_time, start_offset=1500, count=45)

    # More normal traffic during C2 activity
    normal_during = generate_more_normal_traffic(base_time + timedelta(seconds=1500), count=40)

    # Merge C2 and normal traffic (simulating real-world scenario)
    combined = c2_traffic + normal_during
    # Sort by timestamp to interleave them realistically
    combined.sort(key=lambda x: x.split()[0:2] if not x.startswith('#') else ['9999'])
    all_logs.extend(combined)

    # Normal traffic after C2 activity
    normal_after = generate_normal_traffic(base_time + timedelta(seconds=2500), count=30)
    all_logs.extend(normal_after)

    # Print all logs
    for log in all_logs:
        print(log)

    print("#")
    print("# End of DNS query log")
    print(f"# Total queries logged: {len([l for l in all_logs if not l.startswith('#')])}")

if __name__ == "__main__":
    main()
