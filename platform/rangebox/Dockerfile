# OT tooling overlay on the standard RangeBox image.
# The base already ships the GUI desktop, Wireshark, nmap + ICS NSE, tshark, tcpdump.
# This adds the OT pieces that were missing: the mbpoll Modbus CLI and the ICS
# client libraries used as a fallback where no clean CLI tool exists.
FROM opencyberrange/rangebox:lite
USER root
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      mbpoll python3-pip \
 && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages --no-cache-dir pymodbus python-snap7 pycomm3
USER kali
