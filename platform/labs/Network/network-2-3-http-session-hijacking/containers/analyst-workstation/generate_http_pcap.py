#!/usr/bin/env python3
"""
Generate realistic HTTP session hijacking PCAP for MediCare patient portal.
Shows legitimate user session being hijacked by attacker using stolen cookie.
"""

import sys
import random
from datetime import datetime, timedelta
from scapy.all import IP, TCP, Ether, UDP, DNS, DNSQR, DNSRR, Raw, wrpcap

# Network configuration
SERVER_IP = "192.168.100.10"
SERVER_MAC = "00:0c:29:3f:a1:22"
LEGITIMATE_USER_IP = "10.0.1.15"
LEGITIMATE_USER_MAC = "00:0c:29:7b:c3:45"
ATTACKER_IP = "10.0.1.87"
ATTACKER_IP_MAC = "00:0c:29:9f:2d:88"
DNS_SERVER_IP = "8.8.8.8"
DNS_SERVER_MAC = "00:0c:29:11:22:33"
OTHER_USER_IPS = ["10.0.1.23", "10.0.1.34", "10.0.1.56", "10.0.1.67"]

# The stolen session cookie - this is the key to the attack
STOLEN_SESSION_ID = "abc123def456OCR{s3ss10n_c00k13_st0l3n}xyz789"

# TCP sequence tracking
tcp_seq = {}

def get_seq_key(src_ip, dst_ip, sport, dport):
    """Generate key for tracking TCP sequences"""
    return f"{src_ip}:{sport}->{dst_ip}:{dport}"

def get_tcp_seq(src_ip, dst_ip, sport, dport, init=False):
    """Get or initialize TCP sequence number"""
    key = get_seq_key(src_ip, dst_ip, sport, dport)
    if init or key not in tcp_seq:
        tcp_seq[key] = random.randint(1000000, 2000000)
    return tcp_seq[key]

def update_tcp_seq(src_ip, dst_ip, sport, dport, length):
    """Update TCP sequence number"""
    key = get_seq_key(src_ip, dst_ip, sport, dport)
    tcp_seq[key] += length

def create_dns_query(timestamp, src_ip, src_mac, domain):
    """Create DNS query packets"""
    packets = []
    sport = random.randint(50000, 60000)

    # DNS query
    query = (
        Ether(src=src_mac, dst=DNS_SERVER_MAC) /
        IP(src=src_ip, dst=DNS_SERVER_IP) /
        UDP(sport=sport, dport=53) /
        DNS(rd=1, qd=DNSQR(qname=domain))
    )
    query.time = timestamp
    packets.append(query)

    # DNS response
    response = (
        Ether(src=DNS_SERVER_MAC, dst=src_mac) /
        IP(src=DNS_SERVER_IP, dst=src_ip) /
        UDP(sport=53, dport=sport) /
        DNS(
            qr=1, aa=1, rd=1, ra=1,
            qd=DNSQR(qname=domain),
            an=DNSRR(rrname=domain, ttl=300, rdata=SERVER_IP)
        )
    )
    response.time = timestamp + 0.05
    packets.append(response)

    return packets

def create_tcp_handshake(timestamp, src_ip, src_mac, dst_ip, dst_mac, sport, dport):
    """Create TCP three-way handshake"""
    packets = []

    # SYN
    seq_client = get_tcp_seq(src_ip, dst_ip, sport, dport, init=True)
    syn = (
        Ether(src=src_mac, dst=dst_mac) /
        IP(src=src_ip, dst=dst_ip) /
        TCP(sport=sport, dport=dport, flags='S', seq=seq_client)
    )
    syn.time = timestamp
    packets.append(syn)
    update_tcp_seq(src_ip, dst_ip, sport, dport, 1)

    # SYN-ACK
    seq_server = get_tcp_seq(dst_ip, src_ip, dport, sport, init=True)
    syn_ack = (
        Ether(src=dst_mac, dst=src_mac) /
        IP(src=dst_ip, dst=src_ip) /
        TCP(sport=dport, dport=sport, flags='SA', seq=seq_server, ack=seq_client + 1)
    )
    syn_ack.time = timestamp + 0.01
    packets.append(syn_ack)
    update_tcp_seq(dst_ip, src_ip, dport, sport, 1)

    # ACK
    ack = (
        Ether(src=src_mac, dst=dst_mac) /
        IP(src=src_ip, dst=dst_ip) /
        TCP(sport=sport, dport=dport, flags='A',
            seq=get_tcp_seq(src_ip, dst_ip, sport, dport),
            ack=seq_server + 1)
    )
    ack.time = timestamp + 0.02
    packets.append(ack)

    return packets

def create_http_request(timestamp, src_ip, src_mac, dst_ip, dst_mac, sport, dport,
                       method, path, host, cookie=None, extra_headers=""):
    """Create HTTP request packet"""
    seq = get_tcp_seq(src_ip, dst_ip, sport, dport)
    ack = get_tcp_seq(dst_ip, src_ip, dport, sport)

    http_data = f"{method} {path} HTTP/1.1\r\n"
    http_data += f"Host: {host}\r\n"
    http_data += f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
    if cookie:
        http_data += f"Cookie: {cookie}\r\n"
    http_data += extra_headers
    http_data += "Connection: keep-alive\r\n"
    http_data += "\r\n"

    packet = (
        Ether(src=src_mac, dst=dst_mac) /
        IP(src=src_ip, dst=dst_ip) /
        TCP(sport=sport, dport=dport, flags='PA', seq=seq, ack=ack) /
        Raw(load=http_data.encode())
    )
    packet.time = timestamp
    update_tcp_seq(src_ip, dst_ip, sport, dport, len(http_data))

    return packet

def create_http_response(timestamp, src_ip, src_mac, dst_ip, dst_mac, sport, dport,
                        status_code, status_text, body, set_cookie=None, extra_headers=""):
    """Create HTTP response packet"""
    seq = get_tcp_seq(src_ip, dst_ip, sport, dport)
    ack = get_tcp_seq(dst_ip, src_ip, dport, sport)

    http_data = f"HTTP/1.1 {status_code} {status_text}\r\n"
    http_data += "Server: Apache/2.4.41 (Ubuntu)\r\n"
    http_data += "Content-Type: text/html; charset=UTF-8\r\n"
    http_data += f"Content-Length: {len(body)}\r\n"
    if set_cookie:
        http_data += f"Set-Cookie: {set_cookie}\r\n"
    http_data += extra_headers
    http_data += "Connection: keep-alive\r\n"
    http_data += "\r\n"
    http_data += body

    packet = (
        Ether(src=src_mac, dst=dst_mac) /
        IP(src=src_ip, dst=dst_ip) /
        TCP(sport=sport, dport=dport, flags='PA', seq=seq, ack=ack) /
        Raw(load=http_data.encode())
    )
    packet.time = timestamp
    update_tcp_seq(src_ip, dst_ip, sport, dport, len(http_data))

    return packet

def create_tcp_ack(timestamp, src_ip, src_mac, dst_ip, dst_mac, sport, dport):
    """Create TCP ACK packet"""
    seq = get_tcp_seq(src_ip, dst_ip, sport, dport)
    ack = get_tcp_seq(dst_ip, src_ip, dport, sport)

    packet = (
        Ether(src=src_mac, dst=dst_mac) /
        IP(src=src_ip, dst=dst_ip) /
        TCP(sport=sport, dport=dport, flags='A', seq=seq, ack=ack)
    )
    packet.time = timestamp

    return packet

def create_tcp_fin(timestamp, src_ip, src_mac, dst_ip, dst_mac, sport, dport):
    """Create TCP FIN packet"""
    packets = []

    # FIN-ACK from initiator
    seq = get_tcp_seq(src_ip, dst_ip, sport, dport)
    ack = get_tcp_seq(dst_ip, src_ip, dport, sport)
    fin1 = (
        Ether(src=src_mac, dst=dst_mac) /
        IP(src=src_ip, dst=dst_ip) /
        TCP(sport=sport, dport=dport, flags='FA', seq=seq, ack=ack)
    )
    fin1.time = timestamp
    packets.append(fin1)
    update_tcp_seq(src_ip, dst_ip, sport, dport, 1)

    # ACK from receiver
    ack_pkt = (
        Ether(src=dst_mac, dst=src_mac) /
        IP(src=dst_ip, dst=src_ip) /
        TCP(sport=dport, dport=sport, flags='A',
            seq=get_tcp_seq(dst_ip, src_ip, dport, sport),
            ack=get_tcp_seq(src_ip, dst_ip, sport, dport))
    )
    ack_pkt.time = timestamp + 0.01
    packets.append(ack_pkt)

    # FIN-ACK from receiver
    fin2 = (
        Ether(src=dst_mac, dst=src_mac) /
        IP(src=dst_ip, dst=src_ip) /
        TCP(sport=dport, dport=sport, flags='FA',
            seq=get_tcp_seq(dst_ip, src_ip, dport, sport),
            ack=get_tcp_seq(src_ip, dst_ip, sport, dport))
    )
    fin2.time = timestamp + 0.02
    packets.append(fin2)
    update_tcp_seq(dst_ip, src_ip, dport, sport, 1)

    # Final ACK
    final_ack = (
        Ether(src=src_mac, dst=dst_mac) /
        IP(src=src_ip, dst=dst_ip) /
        TCP(sport=sport, dport=dport, flags='A',
            seq=get_tcp_seq(src_ip, dst_ip, sport, dport),
            ack=get_tcp_seq(dst_ip, src_ip, dport, sport))
    )
    final_ack.time = timestamp + 0.03
    packets.append(final_ack)

    return packets

def create_https_encrypted_traffic(timestamp, src_ip, src_mac, count=3):
    """Create some HTTPS encrypted traffic (TLS) as background noise"""
    packets = []
    sport = random.randint(50000, 60000)

    for i in range(count):
        # Encrypted data (just random bytes to simulate TLS)
        encrypted_data = bytes([random.randint(0, 255) for _ in range(random.randint(100, 500))])

        pkt = (
            Ether(src=src_mac, dst=SERVER_MAC) /
            IP(src=src_ip, dst=SERVER_IP) /
            TCP(sport=sport, dport=443, flags='PA',
                seq=random.randint(1000000, 9999999),
                ack=random.randint(1000000, 9999999)) /
            Raw(load=encrypted_data)
        )
        pkt.time = timestamp + (i * 2)
        packets.append(pkt)

    return packets

def generate_pcap(output_file):
    """Generate complete PCAP with session hijacking scenario"""
    packets = []

    # Start time: 3.5 hours ago
    current_time = datetime.now() - timedelta(hours=3, minutes=30)
    base_timestamp = current_time.timestamp()

    print(f"Generating HTTP session hijacking PCAP...")

    # === Background traffic: DNS queries ===
    print("Adding background DNS queries...")
    for offset in [0, 300, 600, 1200, 1800]:
        packets.extend(create_dns_query(
            base_timestamp + offset,
            random.choice(OTHER_USER_IPS),
            "00:0c:29:aa:bb:cc",
            random.choice([
                "www.google.com",
                "api.weather.com",
                "update.microsoft.com",
                "www.cnn.com"
            ])
        ))

    # === Background HTTPS traffic (encrypted) ===
    print("Adding background HTTPS traffic...")
    for offset in [100, 400, 900, 1500]:
        packets.extend(create_https_encrypted_traffic(
            base_timestamp + offset,
            random.choice(OTHER_USER_IPS),
            "00:0c:29:dd:ee:ff"
        ))

    # === LEGITIMATE USER SESSION ===
    print("Creating legitimate user session...")

    # Time: T+0 - DNS query for portal
    time_offset = 2100  # 35 minutes in
    packets.extend(create_dns_query(
        base_timestamp + time_offset,
        LEGITIMATE_USER_IP,
        LEGITIMATE_USER_MAC,
        "portal.medicare.local"
    ))

    # Time: T+1 - User logs in
    time_offset += 5
    sport_login = random.randint(50000, 60000)

    # TCP handshake
    packets.extend(create_tcp_handshake(
        base_timestamp + time_offset,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        SERVER_IP, SERVER_MAC,
        sport_login, 80
    ))

    time_offset += 0.05

    # POST login request
    login_body = "username=john.patient&password=SecurePass123"
    packets.append(create_http_request(
        base_timestamp + time_offset,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        SERVER_IP, SERVER_MAC,
        sport_login, 80,
        "POST", "/api/login", "portal.medicare.local",
        extra_headers=f"Content-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(login_body)}\r\n"
    ))

    time_offset += 0.1

    # Login response with Set-Cookie
    login_response = '{"status":"success","message":"Welcome, John Patient","user_id":12345}'
    packets.append(create_http_response(
        base_timestamp + time_offset,
        SERVER_IP, SERVER_MAC,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        80, sport_login,
        200, "OK",
        login_response,
        set_cookie=f"SESSIONID={STOLEN_SESSION_ID}; Path=/; HttpOnly"
    ))

    time_offset += 0.02
    packets.append(create_tcp_ack(
        base_timestamp + time_offset,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        SERVER_IP, SERVER_MAC,
        sport_login, 80
    ))

    print(f"  -> Session established: SESSIONID={STOLEN_SESSION_ID[:30]}...")

    # Time: T+10 - User requests dashboard
    time_offset += 10
    packets.append(create_http_request(
        base_timestamp + time_offset,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        SERVER_IP, SERVER_MAC,
        sport_login, 80,
        "GET", "/dashboard", "portal.medicare.local",
        cookie=f"SESSIONID={STOLEN_SESSION_ID}"
    ))

    time_offset += 0.1
    dashboard_html = "<html><head><title>Dashboard</title></head><body><h1>Patient Dashboard</h1><p>Welcome back!</p></body></html>"
    packets.append(create_http_response(
        base_timestamp + time_offset,
        SERVER_IP, SERVER_MAC,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        80, sport_login,
        200, "OK",
        dashboard_html
    ))

    time_offset += 0.02
    packets.append(create_tcp_ack(
        base_timestamp + time_offset,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        SERVER_IP, SERVER_MAC,
        sport_login, 80
    ))

    # Time: T+45 - User requests appointments
    time_offset += 35
    packets.append(create_http_request(
        base_timestamp + time_offset,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        SERVER_IP, SERVER_MAC,
        sport_login, 80,
        "GET", "/appointments", "portal.medicare.local",
        cookie=f"SESSIONID={STOLEN_SESSION_ID}"
    ))

    time_offset += 0.1
    appt_html = "<html><body><h1>Your Appointments</h1><ul><li>Dr. Smith - Jan 15</li><li>Lab Work - Jan 20</li></ul></body></html>"
    packets.append(create_http_response(
        base_timestamp + time_offset,
        SERVER_IP, SERVER_MAC,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        80, sport_login,
        200, "OK",
        appt_html
    ))

    time_offset += 0.02
    packets.append(create_tcp_ack(
        base_timestamp + time_offset,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        SERVER_IP, SERVER_MAC,
        sport_login, 80
    ))

    # Close connection
    time_offset += 5
    packets.extend(create_tcp_fin(
        base_timestamp + time_offset,
        LEGITIMATE_USER_IP, LEGITIMATE_USER_MAC,
        SERVER_IP, SERVER_MAC,
        sport_login, 80
    ))

    # === MORE BACKGROUND TRAFFIC ===
    print("Adding more background traffic...")
    for offset in [2500, 2800, 3200, 3600]:
        packets.extend(create_dns_query(
            base_timestamp + offset,
            random.choice(OTHER_USER_IPS),
            "00:0c:29:cc:dd:ee",
            random.choice(["cdn.jsdelivr.net", "fonts.googleapis.com", "ajax.googleapis.com"])
        ))

    # === ATTACKER SESSION (Session Hijacking) ===
    print("Creating attacker session (session hijacking)...")

    # Time: T+420 (7 minutes after legitimate user's login)
    time_offset = 2100 + 420

    # Attacker DNS query
    packets.extend(create_dns_query(
        base_timestamp + time_offset,
        ATTACKER_IP,
        ATTACKER_IP_MAC,
        "portal.medicare.local"
    ))

    time_offset += 5
    sport_attacker = random.randint(50000, 60000)

    # TCP handshake from attacker
    packets.extend(create_tcp_handshake(
        base_timestamp + time_offset,
        ATTACKER_IP, ATTACKER_IP_MAC,
        SERVER_IP, SERVER_MAC,
        sport_attacker, 80
    ))

    time_offset += 0.05

    # Attacker uses STOLEN cookie to access medical records
    print(f"  -> Attacker at {ATTACKER_IP} using stolen cookie!")
    packets.append(create_http_request(
        base_timestamp + time_offset,
        ATTACKER_IP, ATTACKER_IP_MAC,
        SERVER_IP, SERVER_MAC,
        sport_attacker, 80,
        "GET", "/api/medical-records?patient_id=12345", "portal.medicare.local",
        cookie=f"SESSIONID={STOLEN_SESSION_ID}"
    ))

    time_offset += 0.15

    # Server responds with sensitive medical data (attacker successfully hijacked session)
    medical_data = '''{"status":"success","patient_id":12345,"records":[
{"date":"2024-12-01","diagnosis":"Hypertension","doctor":"Dr. Smith"},
{"date":"2024-11-15","diagnosis":"Type 2 Diabetes","doctor":"Dr. Johnson"},
{"date":"2024-10-20","prescription":"Metformin 500mg","doctor":"Dr. Smith"}
],"flag_note":"Session hijacked - OCR{s3ss10n_c00k13_st0l3n}"}'''

    packets.append(create_http_response(
        base_timestamp + time_offset,
        SERVER_IP, SERVER_MAC,
        ATTACKER_IP, ATTACKER_IP_MAC,
        80, sport_attacker,
        200, "OK",
        medical_data
    ))

    time_offset += 0.02
    packets.append(create_tcp_ack(
        base_timestamp + time_offset,
        ATTACKER_IP, ATTACKER_IP_MAC,
        SERVER_IP, SERVER_MAC,
        sport_attacker, 80
    ))

    # Attacker makes another request - viewing prescriptions
    time_offset += 8
    packets.append(create_http_request(
        base_timestamp + time_offset,
        ATTACKER_IP, ATTACKER_IP_MAC,
        SERVER_IP, SERVER_MAC,
        sport_attacker, 80,
        "GET", "/api/prescriptions", "portal.medicare.local",
        cookie=f"SESSIONID={STOLEN_SESSION_ID}"
    ))

    time_offset += 0.1
    prescription_data = '{"prescriptions":["Metformin 500mg","Lisinopril 10mg","Atorvastatin 20mg"]}'
    packets.append(create_http_response(
        base_timestamp + time_offset,
        SERVER_IP, SERVER_MAC,
        ATTACKER_IP, ATTACKER_IP_MAC,
        80, sport_attacker,
        200, "OK",
        prescription_data
    ))

    time_offset += 0.02
    packets.append(create_tcp_ack(
        base_timestamp + time_offset,
        ATTACKER_IP, ATTACKER_IP_MAC,
        SERVER_IP, SERVER_MAC,
        sport_attacker, 80
    ))

    # Attacker closes connection
    time_offset += 3
    packets.extend(create_tcp_fin(
        base_timestamp + time_offset,
        ATTACKER_IP, ATTACKER_IP_MAC,
        SERVER_IP, SERVER_MAC,
        sport_attacker, 80
    ))

    # === Additional legitimate sessions from other users ===
    print("Adding other legitimate user sessions...")

    time_offset += 100
    sport_other = random.randint(50000, 60000)
    other_user = OTHER_USER_IPS[0]
    other_session = "xyz789abc123session" + str(random.randint(1000, 9999))

    packets.extend(create_tcp_handshake(
        base_timestamp + time_offset,
        other_user, "00:0c:29:ff:ee:dd",
        SERVER_IP, SERVER_MAC,
        sport_other, 80
    ))

    time_offset += 0.05

    other_login_body = "username=jane.doe&password=AnotherPass456"
    packets.append(create_http_request(
        base_timestamp + time_offset,
        other_user, "00:0c:29:ff:ee:dd",
        SERVER_IP, SERVER_MAC,
        sport_other, 80,
        "POST", "/api/login", "portal.medicare.local",
        extra_headers=f"Content-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(other_login_body)}\r\n"
    ))

    time_offset += 0.1

    packets.append(create_http_response(
        base_timestamp + time_offset,
        SERVER_IP, SERVER_MAC,
        other_user, "00:0c:29:ff:ee:dd",
        80, sport_other,
        200, "OK",
        '{"status":"success","message":"Welcome, Jane Doe"}',
        set_cookie=f"SESSIONID={other_session}; Path=/; HttpOnly"
    ))

    time_offset += 0.02
    packets.append(create_tcp_ack(
        base_timestamp + time_offset,
        other_user, "00:0c:29:ff:ee:dd",
        SERVER_IP, SERVER_MAC,
        sport_other, 80
    ))

    # Jane accesses her dashboard
    time_offset += 15
    packets.append(create_http_request(
        base_timestamp + time_offset,
        other_user, "00:0c:29:ff:ee:dd",
        SERVER_IP, SERVER_MAC,
        sport_other, 80,
        "GET", "/dashboard", "portal.medicare.local",
        cookie=f"SESSIONID={other_session}"
    ))

    time_offset += 0.1
    packets.append(create_http_response(
        base_timestamp + time_offset,
        SERVER_IP, SERVER_MAC,
        other_user, "00:0c:29:ff:ee:dd",
        80, sport_other,
        200, "OK",
        "<html><body><h1>Welcome Jane!</h1></body></html>"
    ))

    time_offset += 0.02
    packets.append(create_tcp_ack(
        base_timestamp + time_offset,
        other_user, "00:0c:29:ff:ee:dd",
        SERVER_IP, SERVER_MAC,
        sport_other, 80
    ))

    # Close Jane's connection
    time_offset += 10
    packets.extend(create_tcp_fin(
        base_timestamp + time_offset,
        other_user, "00:0c:29:ff:ee:dd",
        SERVER_IP, SERVER_MAC,
        sport_other, 80
    ))

    # === More background traffic at the end ===
    print("Adding final background traffic...")
    for offset in [4000, 4300, 4600, 4900]:
        packets.extend(create_https_encrypted_traffic(
            base_timestamp + offset,
            random.choice(OTHER_USER_IPS),
            "00:0c:29:11:22:33",
            count=2
        ))

    # Write PCAP
    print(f"\nWriting {len(packets)} packets to {output_file}...")
    wrpcap(output_file, packets)

    print(f"✓ PCAP generated successfully!")
    print(f"\nKey details:")
    print(f"  - Legitimate user: {LEGITIMATE_USER_IP}")
    print(f"  - Attacker: {ATTACKER_IP}")
    print(f"  - Stolen SESSIONID: {STOLEN_SESSION_ID[:30]}...")
    print(f"  - Flag embedded in: cookie value and attacker's response data")
    print(f"  - Total packets: {len(packets)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 generate_http_pcap.py <output.pcap>")
        sys.exit(1)

    generate_pcap(sys.argv[1])
