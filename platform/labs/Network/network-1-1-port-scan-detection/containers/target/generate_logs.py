#!/usr/bin/env python3
"""
Generate realistic firewall logs with normal traffic and a port scan.
"""

import random
from datetime import datetime, timedelta

# Configuration
NORMAL_IPS = [
    "10.50.1.15",   # Doctor's workstation
    "10.50.1.22",   # Nurse station
    "10.50.2.8",    # Medical records system
    "10.50.2.45",   # Pharmacy system
    "10.50.3.12",   # Lab system
]

ATTACKER_IP = "203.0.113.66"  # Suspicious external IP

COMMON_SERVICES = [
    (80, "HTTP"),
    (443, "HTTPS"),
    (22, "SSH"),
    (3306, "MySQL"),
    (5432, "PostgreSQL"),
    (8080, "HTTP-ALT"),
]

SCAN_PORTS = list(range(20, 100))  # Attacker scans ports 20-99

def generate_timestamp(base_time, offset_seconds):
    """Generate a timestamp with offset."""
    dt = base_time + timedelta(seconds=offset_seconds)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def generate_normal_traffic(base_time, count=100):
    """Generate normal hospital network traffic."""
    logs = []
    for i in range(count):
        src_ip = random.choice(NORMAL_IPS)
        src_port = random.randint(49152, 65535)
        dst_port, service = random.choice(COMMON_SERVICES)
        action = "ALLOW" if random.random() > 0.1 else "DENY"
        timestamp = generate_timestamp(base_time, i * 30)

        log = f"{timestamp} {action} {src_ip}:{src_port} -> 10.10.3.50:{dst_port} [{service}]"
        logs.append(log)

    return logs

def generate_port_scan(base_time, start_offset=1500):
    """Generate port scanning activity."""
    logs = []
    timestamp_base = base_time + timedelta(seconds=start_offset)

    # Add a comment line indicating scan detection
    scan_start = generate_timestamp(base_time, start_offset)
    logs.append(f"# {scan_start} ALERT: Multiple connection attempts detected from {ATTACKER_IP}")

    # Generate scan attempts
    for i, port in enumerate(SCAN_PORTS):
        src_port = random.randint(30000, 65000)
        timestamp = generate_timestamp(timestamp_base, i * 2)  # 2 seconds between each probe
        action = "DENY"

        service_name = "UNKNOWN"
        for common_port, common_service in COMMON_SERVICES:
            if port == common_port:
                service_name = common_service
                break

        log = f"{timestamp} {action} {ATTACKER_IP}:{src_port} -> 10.10.3.50:{port} [{service_name}]"
        logs.append(log)

    # Add flag in a log comment after scan completes
    scan_end = generate_timestamp(timestamp_base, len(SCAN_PORTS) * 2 + 10)
    logs.append(f"# {scan_end} ANALYSIS: Port scan detected - Source: {ATTACKER_IP}, Ports: {len(SCAN_PORTS)}, Flag: OCR{{p0rt_sc4n_d3t3ct3d}}")

    return logs

def main():
    """Generate complete firewall log file."""
    base_time = datetime(2024, 1, 3, 22, 0, 0)  # Start at 10 PM

    # Generate logs
    print("# MediCare Regional Hospital - Firewall Logs")
    print("# Format: TIMESTAMP ACTION SOURCE_IP:PORT -> DEST_IP:PORT [SERVICE]")
    print("#")

    # Normal traffic before scan
    normal_before = generate_normal_traffic(base_time, count=60)
    for log in normal_before:
        print(log)

    # Port scan activity
    scan_logs = generate_port_scan(base_time, start_offset=1800)
    for log in scan_logs:
        print(log)

    # Normal traffic after scan
    base_after_scan = base_time + timedelta(seconds=2000)
    normal_after = generate_normal_traffic(base_after_scan, count=40)
    for log in normal_after:
        print(log)

    print("#")
    print("# End of log file")

if __name__ == "__main__":
    main()
