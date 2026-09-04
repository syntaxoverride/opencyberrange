# OpenCyberRange UbuntuBox — Browser-Based Ubuntu Desktop
# Architecture: Xvfb + XFCE4 + x11vnc + websockify/noVNC
#
# A general-purpose Ubuntu desktop for students who need a clean Linux
# environment without Kali-specific pentesting tools.  Useful for:
#   - Blue-team / SOC exercises (log analysis, SIEM work)
#   - Programming & scripting labs
#   - System administration exercises
#   - Students who prefer a standard Ubuntu look and feel
#
# Build:
#   docker build -t opencyberrange/ubuntubox:latest UbuntuBox/
#
# Run (standalone test):
#   docker run --rm -p 6080:6080 --shm-size=256m opencyberrange/ubuntubox:latest
#   Open http://localhost:6080/vnc.html

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=en_US.UTF-8 \
    MOZ_DISABLE_CONTENT_SANDBOX=1

# ── Layer 1: Desktop environment + VNC stack ────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11-utils \
    xfce4 \
    xfce4-terminal \
    xfce4-taskmanager \
    dbus-x11 \
    x11vnc \
    novnc \
    websockify \
    fonts-liberation \
    fonts-dejavu-core \
    supervisor \
    sudo \
    locales \
    && sed -i 's/# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && locale-gen \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Layer 2: General-purpose tools ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Networking
    curl wget \
    netcat-openbsd socat tcpdump \
    net-tools iputils-ping dnsutils traceroute iproute2 \
    nmap \
    # Scripting & development
    python3 python3-pip python3-venv \
    git build-essential \
    # Editors & terminal tools
    vim nano tmux \
    # Utilities
    jq file unzip zip tar gzip \
    openssh-client \
    htop tree less \
    gnupg ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Layer 2b: Firefox from Mozilla APT repo (snap stub doesn't work in Docker)
RUN install -d -m 0755 /etc/apt/keyrings && \
    wget -q https://packages.mozilla.org/apt/repo-signing-key.gpg \
         -O /etc/apt/keyrings/packages.mozilla.org.asc && \
    echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" \
         > /etc/apt/sources.list.d/mozilla.list && \
    printf 'Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n' \
         > /etc/apt/preferences.d/mozilla && \
    apt-get update && apt-get install -y firefox \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Layer 3: System configuration ───────────────────────────────────────

# Create non-root user with passwordless sudo
RUN useradd -m -s /bin/bash -G sudo student && \
    echo "student ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    echo "student:student" | chpasswd

# Supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/ubuntubox.conf

# Entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# XFCE preferred applications
RUN mkdir -p /home/student/.config/xfce4 && \
    echo "TerminalEmulator=xfce4-terminal" > /home/student/.config/xfce4/helpers.rc && \
    echo "WebBrowser=firefox"             >> /home/student/.config/xfce4/helpers.rc && \
    echo "FileManager=thunar"             >> /home/student/.config/xfce4/helpers.rc

# OCR desktop wallpaper
COPY ocr-wallpaper-ubuntu.png /usr/share/backgrounds/ocr-wallpaper.png
RUN mkdir -p /home/student/.config/xfce4/xfconf/xfce-perchannel-xml && \
    cat > /home/student/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml << 'XFCEXML'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorscreen" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="/usr/share/backgrounds/ocr-wallpaper.png"/>
          <property name="image-style" type="int" value="5"/>
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.176"/>
            <value type="double" value="0.051"/>
            <value type="double" value="0.251"/>
            <value type="double" value="1.0"/>
          </property>
        </property>
      </property>
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="/usr/share/backgrounds/ocr-wallpaper.png"/>
          <property name="image-style" type="int" value="5"/>
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.176"/>
            <value type="double" value="0.051"/>
            <value type="double" value="0.251"/>
            <value type="double" value="1.0"/>
          </property>
        </property>
      </property>
    </property>
  </property>
</channel>
XFCEXML

# Set ownership
RUN chown -R student:student /home/student

EXPOSE 6080

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD curl -sf http://localhost:6080/vnc.html || exit 1

USER student
WORKDIR /home/student

ENTRYPOINT ["/entrypoint.sh"]
