# OCR Lite Quickstart

OpenCyberRange Lite is a free, self-hosted edition for a single instructor who
runs their own cybersecurity training on their own hardware. You install it from
this repository; the Docker images build on first install, so there is nothing
to download separately and no cloud account to create.

The operator (you) is both the instructor and the administrator. Lite allows one
privileged account, up to five active courses, and an unlimited number of
students. It ships **121 exercises across four tracks** (Windows, Linux, Web, and
Network), all of which run as Docker containers with no KVM or hardware
virtualization required.

A local install is the verified path. A cloud install has not been verified end
to end; expect to adjust firewall rules and the VPN endpoint to suit your
provider.

## What you will do

1. Meet the prerequisites on a clean Ubuntu 22.04+ host.
2. Clone this repository.
3. Run the one installer script and answer its prompts.
4. Complete the first-run setup wizard in your browser (it needs a token the
   installer prints).
5. Create a course and enroll students.

## 1. Prerequisites

- A clean Ubuntu 22.04 or newer host with sudo access.
- Docker and Docker Compose (the installer installs them if missing).
- At least 4 CPU cores, 8 GB RAM, and 40 GB free disk for a small class.
- Outbound internet access for the first install (to pull base images).

See [Prerequisites and Sizing](../../Manual-Lite/00_Server_Deployment/01_Prerequisites.md)
for details.

## 2. Clone the repository

```bash
git clone https://github.com/syntaxoverride/opencyberrange.git opencyberrange
cd opencyberrange
```

## 3. Run the installer

```bash
sudo bash scripts/setup-range-server.sh --install
```

Choose the local-network scenario when prompted, and accept the defaults for
starting services and discovering labs. The installer runs through its phases
(dependencies, WireGuard, firewall, platform, TLS) and builds the platform,
RangeBox desktop, and wiki images. When it finishes it prints a **setup token** —
copy it; you need it in the next step.

## 4. First-run setup wizard

Open the platform in a browser (the installer prints the address). The first
visit shows a four-step setup wizard: **Account**, **Security**, **Modules**,
**Review**. On the Account step, enter your admin username, a real email address,
a password, and the **setup token** the installer printed. Click through Next to
Review, then **Complete Setup**. You are signed in as the administrator.

## 5. Create a course and enroll students

From the admin panel, create a course, activate it, and assign exercises. Share
the course invite code with your students. Students register through the sign-up
form; you approve them from the admin panel, and they join the course with the
invite code.

## Where to go next

- [Local Deployment](../../Manual-Lite/00_Server_Deployment/02_Local_Deployment.md)
- [Instructor Guide](../../Manual-Lite/03_Instructor_Guide/01_Instructor_Dashboard.md)
- [Student Guide](../../Manual-Lite/02_Student_Guide/01_Student_Dashboard.md)
