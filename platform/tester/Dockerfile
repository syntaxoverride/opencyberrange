# ── Stage 1: build a musl-native libsnap7.so ──────────────────────────────
# python-snap7 ships a glibc manylinux binary that will not load on Alpine
# (musl), so ICS S7comm solve-steps fail with "can't find snap7 library".
# Compile the Snap7 C++ library from source against musl here, then copy the
# resulting .so into the runtime image.
FROM alpine:3.19 AS snap7build
RUN apk add --no-cache build-base p7zip curl
WORKDIR /build
RUN curl -fsSL -o snap7.7z \
      "https://sourceforge.net/projects/snap7/files/1.4.2/snap7-full-1.4.2.7z/download" \
 && 7z x -y snap7.7z >/dev/null \
 && cd snap7-full-1.4.2/build/unix \
 && make -f x86_64_linux.mk all \
 && cp ../bin/x86_64-linux/libsnap7.so /build/libsnap7.so

# ── Stage 2: tester sidecar runtime ───────────────────────────────────────
FROM alpine:3.19

RUN apk add --no-cache \
    nmap nmap-scripts \
    curl wget \
    netcat-openbsd \
    lftp \
    openssh-client \
    sshpass \
    samba-client \
    mariadb-client \
    openldap-clients \
    net-snmp-tools \
    python3 \
    py3-pip \
    bind-tools \
    jq \
    bash

# Industrial protocol client libraries so ICS lab solve-steps (Modbus, S7comm,
# EtherNet/IP CIP, OPC-UA) can run from the tester sidecar. DNP3 labs use raw
# sockets and need no extra package.
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    pymodbus==3.6.3 \
    pycomm3 \
    asyncua \
    python-snap7==1.3

# python-snap7's bundled native library is a glibc build and will not load on
# musl. Install the musl-native libsnap7.so compiled in stage 1 where the C
# loader (and python-snap7) will find it.
COPY --from=snap7build /build/libsnap7.so /usr/lib/libsnap7.so
RUN ln -sf /usr/lib/libsnap7.so /usr/lib/libsnap7.so.1

# Keep container alive so backend can docker exec into it
ENTRYPOINT ["tail", "-f", "/dev/null"]
