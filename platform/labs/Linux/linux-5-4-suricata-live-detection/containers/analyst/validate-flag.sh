#!/bin/bash
# ══════════════════════════════════════════════════════════════════════
# Sentinel Defense Corp: IDS Alert Validator
#
# Checks Suricata's eve.json for correctly triggered detection rules
# and extracts indicators of compromise from the captured payloads.
#
# Usage: validate-flag
# ══════════════════════════════════════════════════════════════════════

EVE="/var/log/suricata/eve.json"
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}${CYAN}  Sentinel Defense Corp: IDS Alert Validator${RESET}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════${RESET}"
echo ""

if [ ! -f "$EVE" ]; then
    echo -e "${RED}[ERROR]${RESET} Suricata eve.json not found at ${EVE}"
    echo "        Is Suricata running? Check: pgrep suricata"
    exit 1
fi

ALERT_COUNT=$(jq -r 'select(.alert != null) | .alert.signature' "$EVE" 2>/dev/null | wc -l)
echo -e "${BOLD}Total alerts in eve.json:${RESET} ${ALERT_COUNT}"
echo ""

# ── Check for SQLi detection rule (SID 1000001) ─────────────────────
echo -e "${BOLD}[1/2] Checking for SQL Injection detection rule...${RESET}"

SQLI_URL=$(jq -r 'select(.alert != null) | select(.alert.signature_id == 1000001) | .http.url' "$EVE" 2>/dev/null | head -1)

if [ -z "$SQLI_URL" ] || [ "$SQLI_URL" = "null" ]; then
    echo -e "  ${RED}[FAIL]${RESET} No alert with SID 1000001 found."
    echo "         Write a rule matching SQL injection (UNION SELECT) in HTTP URIs."
    echo "         Rules file: /etc/suricata/rules/local.rules"
    echo "         Reload:     sudo kill -USR2 \$(pgrep suricata)"
    echo ""
    PART1=""
else
    PART1=$(echo "$SQLI_URL" | grep -oP 'campaign=\K[^&]+' 2>/dev/null | head -1)
    echo -e "  ${GREEN}[PASS]${RESET} SQLi rule triggered!"
    echo -e "  ${BOLD}Matched URL:${RESET} ${SQLI_URL}"
    echo -e "  ${BOLD}Campaign tag (Part 1):${RESET} ${CYAN}${PART1}${RESET}"
    echo ""
fi

# ── Check for Command Injection detection rule (SID 1000002) ─────────
echo -e "${BOLD}[2/2] Checking for Command Injection detection rule...${RESET}"

CMDI_PAYLOAD=$(jq -r 'select(.alert != null) | select(.alert.signature_id == 1000002) | .payload_printable' "$EVE" 2>/dev/null | head -1)

if [ -z "$CMDI_PAYLOAD" ] || [ "$CMDI_PAYLOAD" = "null" ]; then
    echo -e "  ${RED}[FAIL]${RESET} No alert with SID 1000002 found."
    echo "         Write a rule matching command injection (cat /etc) in HTTP request bodies."
    echo "         Use the http_client_body content modifier."
    echo ""
    PART2=""
else
    PART2=$(echo "$CMDI_PAYLOAD" | tr '\n' ' ' | grep -oP 'exfil=\K[^& \\]+' 2>/dev/null | head -1)
    echo -e "  ${GREEN}[PASS]${RESET} CMDi rule triggered!"
    echo -e "  ${BOLD}Exfil tag (Part 2):${RESET} ${CYAN}${PART2}${RESET}"
    echo ""
fi

# ── Summary ──────────────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════${RESET}"

if [ -n "$PART1" ] && [ -n "$PART2" ]; then
    echo -e "${GREEN}${BOLD}  Both IDS rules triggered successfully!${RESET}"
    echo ""
    echo -e "  IOC Part 1 (campaign tag): ${BOLD}${PART1}${RESET}"
    echo -e "  IOC Part 2 (exfil tag):    ${BOLD}${PART2}${RESET}"
    echo ""
    echo -e "  ${YELLOW}${BOLD}Next step:${RESET} SSH to the target web portal and examine the"
    echo -e "  nginx access log for the attacker's User-Agent string."
    echo -e "  That gives you Part 3."
    echo ""
    echo -e "  Assemble: ${BOLD}OCR{part1_part2_part3}${RESET}"
else
    echo -e "${RED}${BOLD}  Not all rules are triggering yet.${RESET}"
    echo -e "  Fix the failing rules, reload Suricata, wait 15 seconds, and retry."
fi

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════${RESET}"
echo ""
