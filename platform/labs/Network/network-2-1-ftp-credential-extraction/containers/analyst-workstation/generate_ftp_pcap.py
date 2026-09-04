#!/usr/bin/env python3
"""
Generate realistic PCAP file with FTP traffic including credential leak.
Includes 2-3 hours of network traffic with various protocols as distractors.
"""

from scapy.all import *
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.dns import DNS, DNSQR, DNSRR
from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse
import random
import sys

def generate_dns_traffic(packets, base_time, src_ip, dst_ip="8.8.8.8"):
    """Generate realistic DNS queries as distractor traffic."""
    domains = [
        "google.com", "microsoft.com", "office365.com", "medicare.gov",
        "ehr-system.local", "pacs.medicare.local", "pharmacy.local",
        "lab-results.local", "email.medicare.local"
    ]

    for i in range(30):
        domain = random.choice(domains)
        timestamp = base_time + (i * 120) + random.randint(0, 60)  # Every ~2 minutes

        # DNS Query
        dns_query = IP(src=src_ip, dst=dst_ip) / \
                   UDP(sport=random.randint(50000, 60000), dport=53) / \
                   DNS(rd=1, qd=DNSQR(qname=domain))
        dns_query.time = timestamp
        packets.append(dns_query)

        # DNS Response (simplified)
        dns_resp = IP(src=dst_ip, dst=src_ip) / \
                  UDP(sport=53, dport=dns_query[UDP].sport) / \
                  DNS(id=dns_query[DNS].id, qr=1, aa=0, qd=DNSQR(qname=domain),
                      an=DNSRR(rrname=domain, rdata="192.0.2.1"))
        dns_resp.time = timestamp + 0.05
        packets.append(dns_resp)

def generate_http_traffic(packets, base_time, src_ip, dst_ip="10.50.10.80"):
    """Generate HTTP traffic as distractor."""
    paths = ["/", "/index.html", "/api/patients", "/dashboard", "/reports"]

    for i in range(20):
        timestamp = base_time + (i * 300) + random.randint(0, 120)  # Every ~5 minutes
        sport = random.randint(50000, 60000)

        # TCP handshake
        syn = IP(src=src_ip, dst=dst_ip) / TCP(sport=sport, dport=80, flags="S", seq=1000)
        syn.time = timestamp
        packets.append(syn)

        syn_ack = IP(src=dst_ip, dst=src_ip) / TCP(sport=80, dport=sport, flags="SA", seq=2000, ack=1001)
        syn_ack.time = timestamp + 0.01
        packets.append(syn_ack)

        ack = IP(src=src_ip, dst=dst_ip) / TCP(sport=sport, dport=80, flags="A", seq=1001, ack=2001)
        ack.time = timestamp + 0.02
        packets.append(ack)

        # HTTP GET Request
        http_get = IP(src=src_ip, dst=dst_ip) / TCP(sport=sport, dport=80, flags="PA", seq=1001, ack=2001) / \
                   Raw(load=f"GET {random.choice(paths)} HTTP/1.1\r\nHost: medicare.local\r\n\r\n")
        http_get.time = timestamp + 0.03
        packets.append(http_get)

def generate_failed_ftp_attempts(packets, base_time, src_ip, ftp_server="10.50.5.100"):
    """Generate failed FTP login attempts as distractors."""
    failed_users = ["admin", "root", "test", "backup", "ftp", "guest"]

    for i, username in enumerate(failed_users):
        timestamp = base_time + 3600 + (i * 180)  # Start 1 hour in, every 3 minutes
        sport = random.randint(50000, 60000)
        seq_client = random.randint(10000, 20000)
        seq_server = random.randint(30000, 40000)

        # TCP Handshake for FTP control channel
        syn = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="S", seq=seq_client)
        syn.time = timestamp
        packets.append(syn)

        syn_ack = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="SA", seq=seq_server, ack=seq_client+1)
        syn_ack.time = timestamp + 0.02
        packets.append(syn_ack)

        ack = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="A", seq=seq_client+1, ack=seq_server+1)
        ack.time = timestamp + 0.03
        packets.append(ack)

        # FTP Welcome Banner
        welcome = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="PA", seq=seq_server+1, ack=seq_client+1) / \
                 Raw(load=b"220 MediCare FTP Server Ready\r\n")
        welcome.time = timestamp + 0.05
        packets.append(welcome)
        seq_server += len(welcome[Raw].load)

        # Client ACK
        ack2 = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="A", seq=seq_client+1, ack=seq_server)
        ack2.time = timestamp + 0.06
        packets.append(ack2)

        # USER command
        user_cmd = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="PA", seq=seq_client+1, ack=seq_server) / \
                  Raw(load=f"USER {username}\r\n".encode())
        user_cmd.time = timestamp + 0.5
        packets.append(user_cmd)
        seq_client += len(user_cmd[Raw].load)

        # Server ACK
        ack3 = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="A", seq=seq_server, ack=seq_client)
        ack3.time = timestamp + 0.51
        packets.append(ack3)

        # Password required response
        pass_req = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="PA", seq=seq_server, ack=seq_client) / \
                  Raw(load=f"331 Password required for {username}\r\n".encode())
        pass_req.time = timestamp + 0.52
        packets.append(pass_req)
        seq_server += len(pass_req[Raw].load)

        # PASS command (wrong password)
        pass_cmd = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="PA", seq=seq_client, ack=seq_server) / \
                  Raw(load=b"PASS wrongpass\r\n")
        pass_cmd.time = timestamp + 1.0
        packets.append(pass_cmd)
        seq_client += len(pass_cmd[Raw].load)

        # Login failed response
        fail_resp = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="PA", seq=seq_server, ack=seq_client) / \
                   Raw(load=b"530 Login incorrect\r\n")
        fail_resp.time = timestamp + 1.02
        packets.append(fail_resp)

def generate_successful_ftp_session(packets, base_time, src_ip, ftp_server="10.50.5.100"):
    """Generate successful FTP session with flag in password."""
    timestamp = base_time + 7200  # 2 hours into the capture
    sport = 51234
    seq_client = 15000
    seq_server = 35000

    # TCP Handshake
    syn = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="S", seq=seq_client)
    syn.time = timestamp
    packets.append(syn)

    syn_ack = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="SA", seq=seq_server, ack=seq_client+1)
    syn_ack.time = timestamp + 0.02
    packets.append(syn_ack)

    ack = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="A", seq=seq_client+1, ack=seq_server+1)
    ack.time = timestamp + 0.03
    packets.append(ack)

    # FTP Welcome
    welcome = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="PA", seq=seq_server+1, ack=seq_client+1) / \
             Raw(load=b"220 MediCare Medical Records FTP Server Ready\r\n")
    welcome.time = timestamp + 0.05
    packets.append(welcome)
    seq_server += len(welcome[Raw].load)

    ack2 = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="A", seq=seq_client+1, ack=seq_server)
    ack2.time = timestamp + 0.06
    packets.append(ack2)

    # USER command (successful)
    user_cmd = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="PA", seq=seq_client+1, ack=seq_server) / \
              Raw(load=b"USER medrecords\r\n")
    user_cmd.time = timestamp + 1.0
    packets.append(user_cmd)
    seq_client += len(user_cmd[Raw].load)

    ack3 = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="A", seq=seq_server, ack=seq_client)
    ack3.time = timestamp + 1.01
    packets.append(ack3)

    # Password required
    pass_req = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="PA", seq=seq_server, ack=seq_client) / \
              Raw(load=b"331 Password required for medrecords\r\n")
    pass_req.time = timestamp + 1.02
    packets.append(pass_req)
    seq_server += len(pass_req[Raw].load)

    ack4 = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="A", seq=seq_client, ack=seq_server)
    ack4.time = timestamp + 1.03
    packets.append(ack4)

    # PASS command WITH FLAG
    pass_cmd = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="PA", seq=seq_client, ack=seq_server) / \
              Raw(load=b"PASS OCR{ftp_us3r_p4ssw0rd_l34k}\r\n")
    pass_cmd.time = timestamp + 2.0
    packets.append(pass_cmd)
    seq_client += len(pass_cmd[Raw].load)

    ack5 = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="A", seq=seq_server, ack=seq_client)
    ack5.time = timestamp + 2.01
    packets.append(ack5)

    # Successful login response
    success = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="PA", seq=seq_server, ack=seq_client) / \
             Raw(load=b"230 User medrecords logged in\r\n")
    success.time = timestamp + 2.05
    packets.append(success)
    seq_server += len(success[Raw].load)

    # LIST command
    list_cmd = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="PA", seq=seq_client, ack=seq_server) / \
              Raw(load=b"LIST\r\n")
    list_cmd.time = timestamp + 3.0
    packets.append(list_cmd)
    seq_client += len(list_cmd[Raw].load)

    # List response
    list_resp = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="PA", seq=seq_server, ack=seq_client) / \
               Raw(load=b"150 Opening data connection for directory list\r\n")
    list_resp.time = timestamp + 3.02
    packets.append(list_resp)

    # RETR command (download patient records)
    retr_cmd = IP(src=src_ip, dst=ftp_server) / TCP(sport=sport, dport=21, flags="PA", seq=seq_client, ack=seq_server+len(list_resp[Raw].load)) / \
              Raw(load=b"RETR patient_records.db\r\n")
    retr_cmd.time = timestamp + 5.0
    packets.append(retr_cmd)

    # File transfer response
    retr_resp = IP(src=ftp_server, dst=src_ip) / TCP(sport=21, dport=sport, flags="PA", seq=seq_server+len(list_resp[Raw].load), ack=seq_client+len(retr_cmd[Raw].load)) / \
               Raw(load=b"150 Opening BINARY mode data connection for patient_records.db\r\n")
    retr_resp.time = timestamp + 5.02
    packets.append(retr_resp)

def main(output_file):
    """Generate complete PCAP file."""
    packets = []
    base_time = 1704297600  # Jan 3, 2024 14:00:00

    src_ip = "10.50.2.45"  # Attacker workstation

    print("Generating DNS traffic...")
    generate_dns_traffic(packets, base_time, src_ip)

    print("Generating HTTP traffic...")
    generate_http_traffic(packets, base_time, src_ip)

    print("Generating failed FTP attempts...")
    generate_failed_ftp_attempts(packets, base_time, src_ip)

    print("Generating successful FTP session with flag...")
    generate_successful_ftp_session(packets, base_time, src_ip)

    print(f"Generated {len(packets)} packets")
    print(f"Writing to {output_file}...")

    wrpcap(output_file, packets)
    print("PCAP file created successfully!")

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "medical-records-ftp.pcap"
    main(output)
