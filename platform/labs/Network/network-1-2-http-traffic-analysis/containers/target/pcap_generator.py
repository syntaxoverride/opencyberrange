#!/usr/bin/env python3
"""
PCAP Generator for HTTP Traffic Analysis Lab
Creates a realistic packet capture with HTTP and HTTPS traffic,
including cleartext credentials in an HTTP POST request.
"""

import sys
from scapy.all import *
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.dns import DNS, DNSQR, DNSRR
from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse
import random

def create_tcp_handshake(src_ip, dst_ip, src_port, dst_port, seq_base):
    """Create a TCP 3-way handshake"""
    packets = []

    # SYN
    syn = IP(src=src_ip, dst=dst_ip) / TCP(sport=src_port, dport=dst_port, flags='S', seq=seq_base)
    packets.append(syn)

    # SYN-ACK
    synack = IP(src=dst_ip, dst=src_ip) / TCP(sport=dst_port, dport=src_port, flags='SA', seq=seq_base+1000, ack=seq_base+1)
    packets.append(synack)

    # ACK
    ack = IP(src=src_ip, dst=dst_ip) / TCP(sport=src_port, dport=dst_port, flags='A', seq=seq_base+1, ack=seq_base+1001)
    packets.append(ack)

    return packets, seq_base+1, seq_base+1001

def create_dns_query(src_ip, dst_ip, domain, qtype='A'):
    """Create a DNS query and response"""
    packets = []

    # DNS Query
    dns_query = IP(src=src_ip, dst=dst_ip) / UDP(sport=random.randint(49152, 65535), dport=53) / \
                DNS(rd=1, qd=DNSQR(qname=domain, qtype=qtype))
    packets.append(dns_query)

    # DNS Response
    if qtype == 'A':
        dns_resp = IP(src=dst_ip, dst=src_ip) / UDP(sport=53, dport=dns_query[UDP].sport) / \
                   DNS(id=dns_query[DNS].id, qr=1, aa=1, qd=dns_query[DNS].qd,
                       an=DNSRR(rrname=domain, ttl=300, rdata='10.20.30.40'))
        packets.append(dns_resp)

    return packets

def create_http_request(src_ip, dst_ip, src_port, dst_port, method, path, host, body=None):
    """Create an HTTP request with TCP handshake"""
    packets = []
    seq_base = random.randint(1000000, 9000000)

    # TCP Handshake
    handshake_packets, client_seq, server_seq = create_tcp_handshake(src_ip, dst_ip, src_port, dst_port, seq_base)
    packets.extend(handshake_packets)

    # HTTP Request
    if method == "GET":
        http_request = f"{method} {path} HTTP/1.1\r\n"
        http_request += f"Host: {host}\r\n"
        http_request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
        http_request += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
        http_request += "Connection: keep-alive\r\n"
        http_request += "\r\n"
    elif method == "POST":
        http_request = f"{method} {path} HTTP/1.1\r\n"
        http_request += f"Host: {host}\r\n"
        http_request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
        http_request += "Accept: application/json, text/plain, */*\r\n"
        http_request += "Content-Type: application/x-www-form-urlencoded\r\n"
        if body:
            http_request += f"Content-Length: {len(body)}\r\n"
        http_request += "Connection: keep-alive\r\n"
        http_request += "\r\n"
        if body:
            http_request += body

    req_packet = IP(src=src_ip, dst=dst_ip) / TCP(sport=src_port, dport=dst_port, flags='PA', seq=client_seq, ack=server_seq) / Raw(load=http_request)
    packets.append(req_packet)

    # ACK from server
    ack_packet = IP(src=dst_ip, dst=src_ip) / TCP(sport=dst_port, dport=src_port, flags='A', seq=server_seq, ack=client_seq+len(http_request))
    packets.append(ack_packet)

    # HTTP Response
    if method == "GET":
        http_response = "HTTP/1.1 200 OK\r\n"
        http_response += "Server: nginx/1.18.0\r\n"
        http_response += "Content-Type: text/html; charset=utf-8\r\n"
        http_response += "Content-Length: 156\r\n"
        http_response += "Connection: keep-alive\r\n"
        http_response += "\r\n"
        http_response += "<html><head><title>MediCare Records</title></head><body><h1>Medical Records System</h1><p>Welcome to the MediCare patient records portal.</p></body></html>"
    elif method == "POST":
        http_response = "HTTP/1.1 200 OK\r\n"
        http_response += "Server: nginx/1.18.0\r\n"
        http_response += "Content-Type: application/json\r\n"
        http_response += "Content-Length: 45\r\n"
        http_response += "Connection: keep-alive\r\n"
        http_response += "\r\n"
        http_response += '{"status":"success","message":"Login successful"}'

    resp_packet = IP(src=dst_ip, dst=src_ip) / TCP(sport=dst_port, dport=src_port, flags='PA', seq=server_seq, ack=client_seq+len(http_request)) / Raw(load=http_response)
    packets.append(resp_packet)

    # ACK from client
    final_ack = IP(src=src_ip, dst=dst_ip) / TCP(sport=src_port, dport=dst_port, flags='A', seq=client_seq+len(http_request), ack=server_seq+len(http_response))
    packets.append(final_ack)

    return packets

def create_tls_handshake(src_ip, dst_ip, src_port, dst_port):
    """Create a partial TLS handshake (encrypted, demonstrating HTTPS)"""
    packets = []
    seq_base = random.randint(1000000, 9000000)

    # TCP Handshake
    handshake_packets, client_seq, server_seq = create_tcp_handshake(src_ip, dst_ip, src_port, dst_port, seq_base)
    packets.extend(handshake_packets)

    # TLS Client Hello (simplified - just showing it's encrypted)
    tls_client_hello = bytes.fromhex(
        '16030100' +  # TLS Record: Handshake, TLS 1.0, Length
        'bb010000b70303' +  # Handshake: Client Hello
        ''.join([format(random.randint(0, 255), '02x') for _ in range(32)]) +  # Random bytes
        '00001c' +  # Cipher suites length
        'c02bc02fcca9cca8c02cc030c00ac009c013c014003300390035002f000a' +  # Cipher suites
        '0100'  # Extensions
    )

    tls_hello_packet = IP(src=src_ip, dst=dst_ip) / TCP(sport=src_port, dport=dst_port, flags='PA', seq=client_seq, ack=server_seq) / Raw(load=tls_client_hello)
    packets.append(tls_hello_packet)

    # TLS Server Hello (simplified encrypted response)
    tls_server_hello = bytes.fromhex(
        '160303005d' +  # TLS Record
        '020000590303' +  # Handshake: Server Hello
        ''.join([format(random.randint(0, 255), '02x') for _ in range(32)]) +  # Random bytes
        '00c030000011'  # Session ID and cipher suite
    )

    tls_server_packet = IP(src=dst_ip, dst=src_ip) / TCP(sport=dst_port, dport=src_port, flags='PA', seq=server_seq, ack=client_seq+len(tls_client_hello)) / Raw(load=tls_server_hello)
    packets.append(tls_server_packet)

    # Some encrypted application data (unreadable)
    encrypted_data = bytes([random.randint(0, 255) for _ in range(200)])
    tls_data_header = bytes.fromhex('1703030095')  # TLS Application Data

    app_data_packet = IP(src=src_ip, dst=dst_ip) / TCP(sport=src_port, dport=dst_port, flags='PA', seq=client_seq+len(tls_client_hello), ack=server_seq+len(tls_server_hello)) / Raw(load=tls_data_header + encrypted_data)
    packets.append(app_data_packet)

    return packets

def generate_pcap(output_file):
    """Generate a complete PCAP file with realistic traffic"""
    packets = []

    # Client and server IPs
    client_ip = "192.168.100.50"
    dns_server = "8.8.8.8"
    http_server = "10.20.30.40"
    https_server = "10.20.30.41"

    print(f"Generating PCAP file: {output_file}")

    # 1. DNS Queries (normal traffic)
    print("  [+] Adding DNS queries...")
    packets.extend(create_dns_query(client_ip, dns_server, "www.google.com"))
    packets.extend(create_dns_query(client_ip, dns_server, "medical.medicare.local"))
    packets.extend(create_dns_query(client_ip, dns_server, "portal.healthcare.org"))
    packets.extend(create_dns_query(client_ip, dns_server, "api.medicare.local"))

    # 2. HTTPS Traffic (encrypted - students can't see inside)
    print("  [+] Adding HTTPS traffic (encrypted)...")
    packets.extend(create_tls_handshake(client_ip, https_server, random.randint(49152, 65535), 443))
    packets.extend(create_tls_handshake(client_ip, https_server, random.randint(49152, 65535), 443))

    # 3. HTTP GET Requests (cleartext but no credentials)
    print("  [+] Adding HTTP GET requests...")
    packets.extend(create_http_request(
        client_ip, http_server,
        random.randint(49152, 65535), 80,
        "GET", "/", "medical.medicare.local"
    ))

    packets.extend(create_http_request(
        client_ip, http_server,
        random.randint(49152, 65535), 80,
        "GET", "/patients", "medical.medicare.local"
    ))

    # 4. THE VULNERABLE HTTP POST - Cleartext credentials with FLAG
    print("  [+] Adding HTTP POST with cleartext credentials (FLAG HERE)...")
    credentials_body = "username=dr.johnson&password=OCR{http_cr3d3nt14ls}"
    packets.extend(create_http_request(
        client_ip, http_server,
        random.randint(49152, 65535), 80,
        "POST", "/api/login", "medical.medicare.local",
        body=credentials_body
    ))

    # 5. More normal HTTP traffic after login
    print("  [+] Adding post-authentication HTTP traffic...")
    packets.extend(create_http_request(
        client_ip, http_server,
        random.randint(49152, 65535), 80,
        "GET", "/dashboard", "medical.medicare.local"
    ))

    # 6. More DNS queries
    packets.extend(create_dns_query(client_ip, dns_server, "cdn.medicare.local"))

    # 7. Another HTTPS session (showing secure alternative)
    packets.extend(create_tls_handshake(client_ip, https_server, random.randint(49152, 65535), 443))

    print(f"  [+] Generated {len(packets)} packets")
    print(f"  [+] Writing to {output_file}...")

    # Write PCAP file
    wrpcap(output_file, packets)

    print(f"  [✓] PCAP file created successfully!")
    print(f"\nFlag location: HTTP POST to /api/login")
    print(f"Flag value: OCR{{http_cr3d3nt14ls}}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output.pcap>")
        sys.exit(1)

    output_file = sys.argv[1]
    generate_pcap(output_file)
