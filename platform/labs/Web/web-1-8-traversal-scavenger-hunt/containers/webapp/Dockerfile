FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir flask

# ── Application directory structure ──────────────────────────────────
RUN mkdir -p /app/media/assets /app/docs /app/api/reports

COPY app.py /app/app.py

# ── Legitimate media files ───────────────────────────────────────────
RUN printf 'Cascade Digital Media. Brand Assets Package\n\
=============================================\n\n\
Logo files: cascade-logo-dark.png, cascade-logo-light.png\n\
Brand colors: #1a365d (Navy), #63b3ed (Sky), #e2e8f0 (Silver)\n\
Typography: Inter (headings), Source Sans Pro (body)\n' > /app/media/assets/brand_kit.txt && \
    printf 'Cascade Digital Media. Campaign Archive Q3 2024\n\
================================================\n\n\
Campaign: Summer Launch Series\n\
Impressions: 2.4M | Clicks: 187K | CTR: 7.8%%\n\
Top performing: video-hero-summer-v3.mp4\n' > /app/media/assets/campaign_q3.txt && \
    printf 'Cascade Digital Media. Photo Library Index\n\
============================================\n\n\
Total assets: 12,847 files\n\
Categories: Product (3,201), Lifestyle (4,112), Event (2,890), Stock (2,644)\n\
Storage used: 48.3 GB of 100 GB allocation\n' > /app/media/assets/photo_index.txt

# ── Legitimate documentation files ───────────────────────────────────
RUN printf 'Cascade Digital Media. Employee Onboarding Guide\n\
==================================================\n\n\
1. Complete HR paperwork in BambooHR\n\
2. Set up workstation with IT (ext. 4401)\n\
3. Request access to Confluence and Jira\n\
4. Schedule 1:1 with your team lead\n' > /app/docs/onboarding.txt && \
    printf 'Cascade Digital Media. Content Style Guide v2.3\n\
=================================================\n\n\
Voice: Professional but approachable\n\
Headlines: Title case, max 65 characters\n\
CTAs: Action-oriented, single verb phrases\n' > /app/docs/style_guide.txt && \
    printf 'Cascade Digital Media. Platform Architecture\n\
==============================================\n\n\
Frontend: React 18 + TypeScript\n\
Backend: Flask API (Python 3.11)\n\
Database: PostgreSQL 15\n\
CDN: CloudFront + S3\n' > /app/docs/architecture.txt

# ── Legitimate report files ──────────────────────────────────────────
RUN printf 'Cascade Digital Media. Monthly Analytics Report\n\
================================================\n\n\
Period: October 2024\n\
Total page views: 1,847,203\n\
Unique visitors: 423,891\n\
Avg session duration: 3m 42s\n\
Bounce rate: 34.2%%\n' > /app/api/reports/analytics_oct.txt && \
    printf 'Cascade Digital Media. Revenue Summary Q3\n\
==========================================\n\n\
Ad revenue: $287,400\n\
Subscription revenue: $412,300\n\
Consulting revenue: $94,800\n\
Total Q3: $794,500\n' > /app/api/reports/revenue_q3.txt

# ── Token 1. /opt/cascade/token1.txt ───────────────────────────────
RUN mkdir -p /opt/cascade && \
    printf 'sc4v3ng3\n' > /opt/cascade/token1.txt && \
    chmod 644 /opt/cascade/token1.txt

# ── Token 2. /var/cascade/token2.txt ───────────────────────────────
RUN mkdir -p /var/cascade && \
    printf 'p4th\n' > /var/cascade/token2.txt && \
    chmod 644 /var/cascade/token2.txt

# ── Token 3. /root/token3.txt ──────────────────────────────────────
RUN printf 'pwn\n' > /root/token3.txt && chmod 644 /root/token3.txt

WORKDIR /app
EXPOSE 80
CMD ["python3", "app.py"]
