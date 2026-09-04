#!/usr/bin/env python3
"""
Generate realistic SSH authentication logs with normal traffic and a brute-force attack.
"""

import random
from datetime import datetime, timedelta

# Configuration
HOSPITAL_IPS = [
    "10.50.1.15",   # IT Admin workstation
    "10.50.1.22",   # Senior sysadmin
    "10.50.2.8",    # Database admin
    "10.50.2.45",   # Network admin
    "10.50.3.12",   # Security team
]

LEGITIMATE_USERS = [
    "jthompson",    # John Thompson - IT Admin
    "smiller",      # Sarah Miller - Sysadmin
    "rchen",        # Robert Chen - DB Admin
    "mwilliams",    # Maria Williams - Network Admin
    "dlee",         # David Lee - Security
]

ATTACKER_IP = "185.220.101.77"  # Suspicious external IP

# Common usernames used in brute-force attacks
BRUTEFORCE_USERNAMES = [
    "admin", "root", "user", "test", "guest", "administrator",
    "postgres", "mysql", "oracle", "backup", "deploy", "jenkins",
    "ubuntu", "centos", "debian", "ftpuser", "webmaster", "support",
    "pi", "service", "operator", "default", "nginx", "apache",
    "tomcat", "ansible", "puppet", "chef", "docker", "kubernetes",
    "git", "svn", "www", "ftp", "mail", "sales", "info",
    "server", "dev", "prod", "staging", "api", "app", "web",
    "db", "database", "cache", "redis", "mongo", "elastic",
    "user1", "user2", "test1", "test2", "admin123", "manager",
    "office", "remote", "vpn", "proxy", "scanner", "printer"
]

def generate_timestamp(base_time, offset_seconds):
    """Generate a timestamp with offset."""
    dt = base_time + timedelta(seconds=offset_seconds)
    return dt.strftime("%b %d %H:%M:%S")

def get_random_port():
    """Generate a random high-numbered port for SSH clients."""
    return random.randint(49152, 65535)

def generate_normal_traffic(base_time, count=30):
    """Generate normal hospital SSH authentication traffic."""
    logs = []
    time_offset = 0

    for i in range(count):
        src_ip = random.choice(HOSPITAL_IPS)
        username = random.choice(LEGITIMATE_USERS)
        src_port = get_random_port()
        pid = random.randint(10000, 30000)

        # 90% successful logins, 10% legitimate failures (typos)
        if random.random() > 0.10:
            # Successful login
            timestamp = generate_timestamp(base_time, time_offset)
            log = f"{timestamp} medicare-ssh sshd[{pid}]: Accepted password for {username} from {src_ip} port {src_port} ssh2"
            logs.append(log)
            time_offset += random.randint(300, 900)  # 5-15 minutes between logins
        else:
            # Occasional typo - one failure then success
            timestamp1 = generate_timestamp(base_time, time_offset)
            pid1 = pid
            log1 = f"{timestamp1} medicare-ssh sshd[{pid1}]: Failed password for {username} from {src_ip} port {src_port} ssh2"
            logs.append(log1)

            time_offset += random.randint(3, 10)  # Few seconds to retype

            timestamp2 = generate_timestamp(base_time, time_offset)
            pid2 = pid + 1
            src_port2 = get_random_port()
            log2 = f"{timestamp2} medicare-ssh sshd[{pid2}]: Accepted password for {username} from {src_ip} port {src_port2} ssh2"
            logs.append(log2)

            time_offset += random.randint(300, 900)

    return logs, time_offset

def generate_bruteforce_attack(base_time, start_offset=3600):
    """Generate SSH brute-force attack activity."""
    logs = []
    timestamp_base = base_time + timedelta(seconds=start_offset)

    # Add a comment line indicating attack detection
    attack_start = generate_timestamp(base_time, start_offset)
    logs.append(f"# {attack_start} SECURITY ALERT: Multiple failed SSH authentication attempts detected")
    logs.append(f"# Source IP: {ATTACKER_IP} - Monitoring for brute-force attack")

    # Generate 60 brute-force attempts over ~10 minutes
    num_attempts = 60
    for i in range(num_attempts):
        username = random.choice(BRUTEFORCE_USERNAMES)
        src_port = get_random_port()
        pid = random.randint(30000, 50000)
        time_offset = i * random.randint(8, 15)  # 8-15 seconds between attempts
        timestamp = generate_timestamp(timestamp_base, time_offset)

        # Mix of invalid users and valid usernames with wrong passwords
        if random.random() > 0.3:
            # Invalid user
            log = f"{timestamp} medicare-ssh sshd[{pid}]: Failed password for invalid user {username} from {ATTACKER_IP} port {src_port} ssh2"
        else:
            # Real username but wrong password
            log = f"{timestamp} medicare-ssh sshd[{pid}]: Failed password for {username} from {ATTACKER_IP} port {src_port} ssh2"

        logs.append(log)

    # Add flag in a security analysis comment after attack
    final_time_offset = num_attempts * 15 + 60
    attack_end = generate_timestamp(timestamp_base, final_time_offset)
    logs.append(f"# {attack_end} SECURITY ANALYSIS COMPLETE")
    logs.append(f"# Attack detected from {ATTACKER_IP}")
    logs.append(f"# Total failed attempts: {num_attempts}")
    logs.append(f"# Unique usernames tried: {len(set(BRUTEFORCE_USERNAMES[:num_attempts]))}")
    logs.append(f"# Attack pattern: Dictionary-based SSH brute-force")
    logs.append(f"# Recommendation: Block IP immediately, review fail2ban configuration")
    logs.append(f"# Flag: OCR{{brut3_f0rc3_d3t3ct3d}}")
    logs.append(f"# IP has been added to blocklist")

    return logs, final_time_offset

def generate_session_logs(base_time, time_offset, count=5):
    """Generate some session open/close logs for realism."""
    logs = []

    for i in range(count):
        src_ip = random.choice(HOSPITAL_IPS)
        username = random.choice(LEGITIMATE_USERS)
        pid = random.randint(10000, 30000)

        # Session opened
        timestamp1 = generate_timestamp(base_time, time_offset)
        log1 = f"{timestamp1} medicare-ssh sshd[{pid}]: pam_unix(sshd:session): session opened for user {username} by (uid=0)"
        logs.append(log1)

        time_offset += random.randint(600, 3600)  # Session lasts 10-60 minutes

        # Session closed
        timestamp2 = generate_timestamp(base_time, time_offset)
        log2 = f"{timestamp2} medicare-ssh sshd[{pid}]: pam_unix(sshd:session): session closed for user {username}"
        logs.append(log2)

        time_offset += random.randint(300, 900)

    return logs, time_offset

def main():
    """Generate complete SSH auth.log file."""
    base_time = datetime(2024, 1, 15, 8, 0, 0)  # Start at 8 AM

    print("# MediCare Regional Hospital - SSH Authentication Logs")
    print("# Server: medicare-ssh-server.medicare.local")
    print("# Log file: /var/log/auth.log")
    print("#")

    all_logs = []

    # Morning normal traffic (8 AM - 11 AM)
    morning_logs, time_offset = generate_normal_traffic(base_time, count=15)
    all_logs.extend(morning_logs)

    # Some session activity
    session_logs1, time_offset = generate_session_logs(base_time, time_offset, count=3)
    all_logs.extend(session_logs1)

    # Brute-force attack starts around 11 AM
    attack_start_offset = time_offset + 600  # 10 minutes after last activity
    attack_logs, attack_duration = generate_bruteforce_attack(base_time, start_offset=attack_start_offset)
    all_logs.extend(attack_logs)

    # Afternoon normal traffic resumes after attack (attackers got blocked)
    afternoon_base = base_time + timedelta(seconds=attack_start_offset + attack_duration + 600)
    afternoon_logs, _ = generate_normal_traffic(afternoon_base, count=15)
    all_logs.extend(afternoon_logs)

    # Print all logs (they're already chronological)
    for log in all_logs:
        print(log)

    print("#")
    print("# End of log file")
    print("# Note: Attacker IP has been blocked by fail2ban after detecting brute-force pattern")

if __name__ == "__main__":
    main()
