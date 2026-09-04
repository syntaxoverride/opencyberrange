#!/usr/bin/env python3
"""
Generate realistic PCAP file with SMTP email traffic including data exfiltration.
Includes 3-4 hours of network traffic with multiple emails and distractors.
"""

from scapy.all import *
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.dns import DNS, DNSQR, DNSRR
import random
import sys

def tcp_handshake(packets, timestamp, src_ip, dst_ip, sport, dport):
    """Generate TCP 3-way handshake."""
    seq_client = random.randint(10000, 50000)
    seq_server = random.randint(10000, 50000)

    # SYN
    syn = IP(src=src_ip, dst=dst_ip) / TCP(sport=sport, dport=dport, flags="S", seq=seq_client)
    syn.time = timestamp
    packets.append(syn)

    # SYN-ACK
    syn_ack = IP(src=dst_ip, dst=src_ip) / TCP(sport=dport, dport=sport, flags="SA", seq=seq_server, ack=seq_client+1)
    syn_ack.time = timestamp + 0.01
    packets.append(syn_ack)

    # ACK
    ack = IP(src=src_ip, dst=dst_ip) / TCP(sport=sport, dport=dport, flags="A", seq=seq_client+1, ack=seq_server+1)
    ack.time = timestamp + 0.02
    packets.append(ack)

    return seq_client + 1, seq_server + 1

def smtp_exchange(packets, timestamp, src_ip, dst_ip, sport, seq_c, seq_s, data):
    """Generate SMTP command/response exchange."""
    current_time = timestamp

    for line in data:
        if line.startswith("C:"):
            # Client command
            payload = line[2:].strip() + "\r\n"
            pkt = IP(src=src_ip, dst=dst_ip) / TCP(sport=sport, dport=25, flags="PA", seq=seq_c, ack=seq_s) / Raw(load=payload)
            pkt.time = current_time
            packets.append(pkt)
            seq_c += len(payload)
            current_time += 0.05
        elif line.startswith("S:"):
            # Server response
            payload = line[2:].strip() + "\r\n"
            pkt = IP(src=dst_ip, dst=src_ip) / TCP(sport=25, dport=sport, flags="PA", seq=seq_s, ack=seq_c) / Raw(load=payload)
            pkt.time = current_time
            packets.append(pkt)
            seq_s += len(payload)
            current_time += 0.05

    return seq_c, seq_s, current_time

def generate_legitimate_email(packets, base_time, offset_minutes, src_ip, smtp_server="10.50.10.25"):
    """Generate a legitimate email conversation."""
    timestamp = base_time + (offset_minutes * 60)
    sport = random.randint(50000, 60000)

    seq_c, seq_s = tcp_handshake(packets, timestamp, src_ip, smtp_server, sport, 25)
    timestamp += 0.1

    smtp_data = [
        "S: 220 mail.medicare.local ESMTP Postfix",
        "C: EHLO workstation.local",
        "S: 250-mail.medicare.local",
        "S: 250-SIZE 10240000",
        "S: 250 HELP",
        f"C: MAIL FROM:<nurse@medicare.local>",
        "S: 250 OK",
        f"C: RCPT TO:<doctor@medicare.local>",
        "S: 250 OK",
        "C: DATA",
        "S: 354 End data with <CR><LF>.<CR><LF>",
        "C: From: nurse@medicare.local",
        "C: To: doctor@medicare.local",
        "C: Subject: Patient Lab Results Ready",
        "C: Date: Wed, 03 Jan 2024 14:35:00 -0600",
        "C: ",
        "C: Dr. Smith,",
        "C: ",
        "C: The lab results for patient Johnson are ready for review.",
        "C: Please check the EHR system when you have a moment.",
        "C: ",
        "C: Thanks,",
        "C: Nurse Parker",
        "C: .",
        "S: 250 OK: queued as AB123456",
        "C: QUIT",
        "S: 221 Bye"
    ]

    smtp_exchange(packets, timestamp, src_ip, smtp_server, sport, seq_c, seq_s, smtp_data)

def generate_internal_emails(packets, base_time):
    """Generate multiple legitimate internal emails as distractors."""
    internal_ips = ["10.50.2.15", "10.50.2.22", "10.50.3.18", "10.50.4.25"]

    # Email 1: 15 minutes in
    generate_legitimate_email(packets, base_time, 15, internal_ips[0])

    # Email 2: 45 minutes in
    timestamp = base_time + (45 * 60)
    sport = random.randint(50000, 60000)
    smtp_server = "10.50.10.25"

    seq_c, seq_s = tcp_handshake(packets, timestamp, internal_ips[1], smtp_server, sport, 25)
    smtp_data = [
        "S: 220 mail.medicare.local ESMTP Postfix",
        "C: EHLO admin-pc.local",
        "S: 250-mail.medicare.local",
        "S: 250 HELP",
        "C: MAIL FROM:<it-admin@medicare.local>",
        "S: 250 OK",
        "C: RCPT TO:<helpdesk@medicare.local>",
        "S: 250 OK",
        "C: DATA",
        "S: 354 End data with <CR><LF>.<CR><LF>",
        "C: From: it-admin@medicare.local",
        "C: To: helpdesk@medicare.local",
        "C: Subject: Password Reset Request",
        "C: ",
        "C: Please reset password for user jsmith.",
        "C: .",
        "S: 250 OK",
        "C: QUIT",
        "S: 221 Bye"
    ]
    smtp_exchange(packets, timestamp + 0.1, internal_ips[1], smtp_server, sport, seq_c, seq_s, smtp_data)

    # Email 3: 90 minutes in
    generate_legitimate_email(packets, base_time, 90, internal_ips[2])

    # Email 4: 150 minutes in
    generate_legitimate_email(packets, base_time, 150, internal_ips[3])

def generate_exfiltration_email(packets, base_time):
    """Generate the suspicious data exfiltration email with flag."""
    timestamp = base_time + (120 * 60)  # 2 hours into capture
    src_ip = "10.50.4.33"  # Database admin workstation
    smtp_server = "10.50.10.25"
    sport = 52441

    seq_c, seq_s = tcp_handshake(packets, timestamp, src_ip, smtp_server, sport, 25)
    timestamp += 0.1

    smtp_data = [
        "S: 220 mail.medicare.local ESMTP Postfix",
        "C: EHLO db-admin.local",
        "S: 250-mail.medicare.local",
        "S: 250-SIZE 10240000",
        "S: 250 HELP",
        "C: MAIL FROM:<dbadmin@medicare.local>",
        "S: 250 OK",
        "C: RCPT TO:<external.contact@protonmail.com>",  # EXTERNAL EMAIL - RED FLAG
        "S: 250 OK",
        "C: DATA",
        "S: 354 End data with <CR><LF>.<CR><LF>",
        "C: From: dbadmin@medicare.local",
        "C: To: external.contact@protonmail.com",
        "C: Subject: Database Export - Confidential",  # SUSPICIOUS SUBJECT
        "C: Date: Wed, 03 Jan 2024 16:15:23 -0600",
        "C: ",
        "C: Here is the patient database export you requested.",
        "C: ",
        "C: Total records: 15,847 patient files",
        "C: Includes: Names, DOB, SSN, diagnoses, medications",
        "C: ",
        "C: Access credentials for the backup server:",
        "C: Username: backup_admin",
        "C: Password: OCR{smtp_d4t4_3xf1ltr4t10n}",  # FLAG HERE
        "C: ",
        "C: Database dump attached (see file share link)",
        "C: https://filestorage.external.com/share/Ab7Yx23K",
        "C: ",
        "C: Let me know if you need anything else.",
        "C: ",
        "C: - DB Admin",
        "C: .",
        "S: 250 OK: queued as XY987654",
        "C: QUIT",
        "S: 221 Bye"
    ]

    smtp_exchange(packets, timestamp, src_ip, smtp_server, sport, seq_c, seq_s, smtp_data)

def generate_dns_traffic(packets, base_time):
    """Generate DNS queries as background traffic."""
    domains = ["google.com", "microsoft.com", "medicare.gov", "mail.medicare.local"]

    for i in range(40):
        timestamp = base_time + (i * 180) + random.randint(0, 60)
        src_ip = f"10.50.{random.randint(1,5)}.{random.randint(10,50)}"

        dns_query = IP(src=src_ip, dst="8.8.8.8") / \
                   UDP(sport=random.randint(50000, 60000), dport=53) / \
                   DNS(rd=1, qd=DNSQR(qname=random.choice(domains)))
        dns_query.time = timestamp
        packets.append(dns_query)

def main(output_file):
    """Generate complete PCAP file."""
    packets = []
    base_time = 1704297600  # Jan 3, 2024 14:00:00

    print("Generating DNS traffic...")
    generate_dns_traffic(packets, base_time)

    print("Generating legitimate internal emails...")
    generate_internal_emails(packets, base_time)

    print("Generating data exfiltration email with flag...")
    generate_exfiltration_email(packets, base_time)

    print(f"Generated {len(packets)} packets")
    print(f"Writing to {output_file}...")

    # Sort by timestamp
    packets.sort(key=lambda x: x.time)

    wrpcap(output_file, packets)
    print("PCAP file created successfully!")
    print(f"Suspicious email timestamp: ~2 hours into capture (16:15)")
    print(f"Look for external recipient: external.contact@protonmail.com")
    print(f"Flag in email body: OCR{{smtp_d4t4_3xf1ltr4t10n}}")

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "email-exfiltration.pcap"
    main(output)
