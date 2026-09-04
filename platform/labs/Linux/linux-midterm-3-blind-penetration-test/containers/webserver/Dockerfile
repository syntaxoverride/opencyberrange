FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir flask

# -- Document root and config directory ---------------------------------
RUN mkdir -p /var/www/apex-app/docs /var/www/apex-app/config

# Legitimate downloadable documents
RUN printf 'APEX MERIDIAN GROUP. CORPORATE BROCHURE\n\
============================================\n\
\n\
Apex Meridian Group is a management consulting firm specializing in\n\
operational excellence, digital transformation, and strategic advisory\n\
services for mid-market enterprises across the Southeast United States.\n\
\n\
Founded: 2016\n\
Headquarters: Charlotte, NC\n\
Employees: 280+\n\
Offices: Charlotte, Raleigh, Atlanta, Nashville\n\
\n\
Core Practice Areas:\n\
  - Operational Strategy & Process Improvement\n\
  - Technology Advisory & Digital Transformation\n\
  - Mergers & Acquisitions Due Diligence\n\
  - Regulatory Compliance & Risk Management\n\
\n\
Contact: info@apexmeridian.com\n' > /var/www/apex-app/docs/brochure.txt

RUN printf 'APEX MERIDIAN GROUP. SERVICE PRICING\n\
======================================\n\
\n\
Engagement Models:\n\
\n\
  STRATEGIC ADVISORY\n\
    Fixed-fee engagement: $45,000 - $120,000\n\
    Duration: 4-12 weeks\n\
    Includes: Assessment, roadmap, executive briefing\n\
\n\
  OPERATIONAL EXCELLENCE\n\
    Monthly retainer: $18,000 - $35,000\n\
    Duration: 6-18 months\n\
    Includes: Process mapping, KPI development, change management\n\
\n\
  TECHNOLOGY TRANSFORMATION\n\
    Project-based: $75,000 - $500,000\n\
    Duration: 3-24 months\n\
    Includes: Architecture review, vendor selection, implementation oversight\n\
\n\
  COMPLIANCE & RISK\n\
    Assessment fee: $25,000 - $60,000\n\
    Ongoing monitoring: $8,000/month\n\
\n\
All pricing subject to scope and complexity. Contact sales@apexmeridian.com\n' > /var/www/apex-app/docs/pricing.txt

# -- Configuration files (traversal targets) ----------------------------
RUN printf 'APP_NAME=Apex Meridian Platform\n\
APP_ENV=production\n\
APP_VERSION=2.4.1\n\
\n\
BACKEND_SSH_HOST=apex-backend\n\
BACKEND_SSH_USER=deploy\n\
BACKEND_SSH_PASS=Ap3x_D3pl0y_2024#\n\
BACKEND_SSH_PORT=22\n\
\n\
DB_HOST=db.internal.apexmeridian.local\n\
DB_NAME=apex_prod\n\
DB_USER=app_svc\n\
DB_PASS=internal_only\n' > /var/www/apex-app/config/app.env

# Assessment marker (token 1)
RUN printf 'bl1nd\n' > /var/www/apex-app/config/assessment_marker.txt

COPY app.py /var/www/apex-app/app.py

WORKDIR /var/www/apex-app
EXPOSE 80
CMD ["python3", "app.py"]
