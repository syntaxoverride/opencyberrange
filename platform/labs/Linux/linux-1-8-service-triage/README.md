# Linux 1.8: Service Triage

**Reinforcement Lab (Unguided) | Week 1 | Beginner | ~40 minutes**

## Overview

This is a reinforcement lab for Week 1 reconnaissance skills. Students face
three hosts on a simulated DMZ. Two are decoys running generic services, and
one is the genuine Vanguard Logistics production server. Students must scan all
three, correlate banners and page content to identify the real target, then
interact with its services to extract a three-part composite flag.

## Hosts

| Host           | IP Offset | Role   | Services                        |
|----------------|-----------|--------|---------------------------------|
| target-alpha   | 14        | Decoy  | nginx (Under Construction), SSH |
| target-bravo   | 29        | Decoy  | Apache (403 Forbidden), FTP     |
| target-charlie | 43        | Target | nginx, FTP, Custom (port 9999)  |

## Skills Practiced

- Multi-host network scanning with nmap
- Service version detection and banner analysis
- Differentiating real targets from decoys
- HTTP, FTP, and custom protocol interaction
- Composite flag assembly

## Flag

Format: `OCR{token1_token2_token3}`: three tokens collected from
target-charlie's web page, FTP server, and custom service.
