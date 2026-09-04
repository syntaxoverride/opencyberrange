# OpenCyberRange RangeBox — Browser-Based Kali Attack Desktop
# Architecture: Xvfb + XFCE4 + x11vnc + websockify/noVNC
#
# Build:
#   docker build -t opencyberrange/rangebox:lite --target lite RangeBox/
#   docker build -t opencyberrange/rangebox:full RangeBox/
#
# Run (standalone test):
#   docker run --rm -p 6080:6080 --shm-size=256m opencyberrange/rangebox:lite
#   Open http://localhost:6080/vnc.html

FROM kalilinux/kali-rolling AS lite

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

# ── Layer 2: Core pentesting tools ─────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Reconnaissance & enumeration
    nmap masscan gobuster dirb nikto whatweb \
    enum4linux smbclient smbmap dnsrecon \
    # Active Directory & Windows
    netexec evil-winrm \
    # Exploitation
    sqlmap \
    # Remote access
    freerdp-x11 \
    # Password attacks
    hydra medusa john hashcat \
    # Web & networking
    curl wget \
    netcat-openbsd ncat socat tcpdump \
    net-tools iputils-ping dnsutils traceroute iproute2 \
    # Packet analysis
    tshark wireshark \
    # Database clients
    default-mysql-client \
    # SNMP
    snmp onesixtyone \
    # Forensics & analysis
    binwalk foremost libimage-exiftool-perl sleuthkit \
    # Network defense
    suricata \
    # Scripting & development
    python3 python3-pip python3-venv \
    git \
    # SSH utilities
    openssh-client sshpass ftp \
    # Editors & terminal tools
    vim nano tmux \
    # Utilities
    jq xxd file unzip \
    # Firewall (gateway blocking in entrypoint)
    iptables \
    # Local DNS for clean reverse lookups (PTR from /etc/hosts)
    dnsmasq \
    # Browser for web exploitation labs
    firefox-esr \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Layer 3: Python tools ──────────────────────────────────────────────
RUN pip3 install --no-cache-dir --break-system-packages \
    impacket \
    volatility3 \
    requests \
    beautifulsoup4 \
    && ln -sf /usr/local/bin/vol /usr/local/bin/vol3 \
    && ln -sf /usr/bin/python3 /usr/local/bin/python \
    && ln -sf /usr/share/doc/python3-impacket/examples/mssqlclient.py /usr/local/bin/mssqlclient.py \
    && chmod +x /usr/share/doc/python3-impacket/examples/mssqlclient.py

# ── Layer 4: Wordlists ────────────────────────────────────────────────
RUN mkdir -p /usr/share/seclists && \
    curl -sfL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
        -o /usr/share/seclists/common.txt && \
    curl -sfL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/directory-list-2.3-medium.txt \
        -o /usr/share/seclists/directory-list-2.3-medium.txt && \
    curl -sfL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Leaked-Databases/rockyou-75.txt \
        -o /usr/share/seclists/rockyou-75.txt || true

# ── Layer 5: System configuration ─────────────────────────────────────

# Create non-root user with passwordless sudo and passwordless su to root
RUN useradd -m -s /bin/bash -G sudo kali && \
    echo "kali ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    echo "kali:kali" | chpasswd && \
    passwd -d root

# Supervisor config (alternative process manager)
COPY supervisord.conf /etc/supervisor/conf.d/rangebox.conf

# Entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# XFCE preferred applications — ensure terminal icon opens the terminal, not the browser
RUN mkdir -p /home/kali/.config/xfce4 && \
    echo "TerminalEmulator=xfce4-terminal" > /home/kali/.config/xfce4/helpers.rc && \
    echo "WebBrowser=firefox-esr"        >> /home/kali/.config/xfce4/helpers.rc && \
    echo "FileManager=thunar"            >> /home/kali/.config/xfce4/helpers.rc

# OCR desktop wallpaper
COPY ocr-wallpaper.png /usr/share/backgrounds/ocr-wallpaper.png
RUN mkdir -p /home/kali/.config/xfce4/xfconf/xfce-perchannel-xml && \
    cat > /home/kali/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml << 'XFCEXML'
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
            <value type="double" value="0.0"/>
            <value type="double" value="0.0"/>
            <value type="double" value="0.0"/>
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
            <value type="double" value="0.0"/>
            <value type="double" value="0.0"/>
            <value type="double" value="0.0"/>
            <value type="double" value="1.0"/>
          </property>
        </property>
      </property>
    </property>
  </property>
</channel>
XFCEXML

# Standard XDG desktop folders + Thunar icon view
RUN mkdir -p /home/kali/Desktop /home/kali/Documents /home/kali/Downloads \
             /home/kali/Music /home/kali/Pictures /home/kali/Public \
             /home/kali/Templates /home/kali/Videos /home/kali/Scripts && \
    mkdir -p /home/kali/.config && \
    cat > /home/kali/.config/user-dirs.dirs << 'XDGDIRS'
XDG_DESKTOP_DIR="$HOME/Desktop"
XDG_DOWNLOAD_DIR="$HOME/Downloads"
XDG_TEMPLATES_DIR="$HOME/Templates"
XDG_PUBLICSHARE_DIR="$HOME/Public"
XDG_DOCUMENTS_DIR="$HOME/Documents"
XDG_MUSIC_DIR="$HOME/Music"
XDG_PICTURES_DIR="$HOME/Pictures"
XDG_VIDEOS_DIR="$HOME/Videos"
XDGDIRS

RUN mkdir -p /home/kali/.config/Thunar && \
    cat > /home/kali/.config/Thunar/thunarrc << 'THUNARRC'
[Configuration]
LastView=ThunarIconView
DefaultView=ThunarIconView
LastIconViewZoomLevel=THUNAR_ZOOM_LEVEL_100_PERCENT
THUNARRC

# Fix zsh prompt: replace Korean ㉿ glyph with plain @ (font doesn't include it)
RUN sed -i "s/prompt_symbol=㉿/prompt_symbol='@'/" /home/kali/.zshrc

# Login banner: warn that external internet is not available
RUN { echo ''; \
      echo '# ── RangeBox login banner ──'; \
      echo 'if [ -z "$_RANGEBOX_BANNER_SHOWN" ]; then'; \
      echo '  export _RANGEBOX_BANNER_SHOWN=1'; \
      echo '  echo ""'; \
      echo '  echo "  ========================================"'; \
      echo '  echo "  OpenCyberRange RangeBox"'; \
      echo '  echo "  ========================================"'; \
      echo '  echo "  NOTE: External internet is DISABLED."'; \
      echo '  echo "  All required tools are pre-installed."'; \
      echo '  echo "  Type \"which <tool>\" to verify a tool"'; \
      echo '  echo "  is available."'; \
      echo '  echo "  ========================================"'; \
      echo '  echo ""'; \
      echo 'fi'; \
    } | tee -a /home/kali/.bashrc >> /home/kali/.zshrc

# Set ownership
RUN chown -R kali:kali /home/kali

EXPOSE 6080

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD curl -sf http://localhost:6080/vnc.html || exit 1

USER kali
WORKDIR /home/kali

ENTRYPOINT ["/entrypoint.sh"]

# ── Full image: adds Metasploit ────────────────────────────────────────
FROM lite AS full

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    metasploit-framework \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

USER kali
WORKDIR /home/kali
ENTRYPOINT ["/entrypoint.sh"]
