# SDS Middleware with FastAPI

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

Deploy the entire application with one command:

```bash
./docker-deploy.sh up
```

This starts:
- ✅ Application server on port 8080
- ✅ MySQL database on port 3306
- ✅ Persistent storage volumes with read/write permissions
- ✅ Network connectivity between services

**Access Points:**
- Admin Console: http://localhost:8080/admin/
- Operations Console: http://localhost:8080/ops/
- API: http://localhost:8080/

**Full Docker Guide**: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

### Option 2: Local Development

```bash
# Start the server locally
./run.sh

# Access the admin console
./start_admin_console.sh

# Access the operations console
./start_ops_console.sh
```

---

## 🎯 New Features

### Operations Console

Monitor and manage system operations with real-time storage tracking!

**Access**: `http://localhost:8080/ops/`  
**Default Secret Code**: `ops-secret-2026`

#### Features:
- 🔐 Secure authentication with separate secret code
- 💾 Storage monitoring for caches and jobs folders
- 📊 Color-coded usage indicators (Green/Orange/Red)
- 🔄 Auto-refresh every 30 seconds
- 📈 Real-time capacity monitoring

**Quick Start:**
```bash
# Start the server
./run.sh

# Open the operations console
./start_ops_console.sh
```

**Documentation:**
- [Operations Console Guide](OPERATIONS_CONSOLE.md) - Complete usage guide
- [Visual Guide](OPERATIONS_CONSOLE_VISUAL_GUIDE.md) - Screenshots and UI overview
- [Quick Reference](OPS_CONSOLE_QUICK_REF.md) - Quick reference card

### System Admin Console

A secure web-based admin console is now available for managing system configuration!

**Access**: `http://localhost:8080/admin/`  
**Default Secret Code**: `admin-secret-2026`

#### Features:
- 🔐 Secure authentication with secret code
- 📝 View and edit all configuration fields from `sds.cfg`
- 💾 Automatic backups before changes
- ✅ Real-time validation
- 🎨 Modern, responsive web interface

**Quick Start:**
```bash
# Start the server
./run.sh

# Open the admin console
open http://localhost:8080/admin/

# Or use the quick start script
./start_admin_console.sh
```

**Documentation:**
- [Admin Console Guide](ADMIN_CONSOLE.md) - Complete usage guide
- [Visual Guide](ADMIN_CONSOLE_VISUAL_GUIDE.md) - Screenshots and UI overview
- [Implementation Summary](ADMIN_CONSOLE_SUMMARY.md) - Technical details

---

## Security

This application implements client secret authentication for all API calls except those originating from localhost. The system supports both a default client secret and site-specific client secrets.

### Configuration

Configure your client secrets in the `app/core/sds.cfg` file:

```ini
[webserver]
client_secret=your-default-client-secret-here

# Site-specific client secrets
[site_site1]
client_secret=site1-secret-key-12345

[site_site2]
client_secret=site2-secret-key-67890

[site_site3]
client_secret=site3-secret-key-abcde
```

### Site Identification

The system determines which site a request is coming from using the following methods (in order of precedence):

1. **X-Site Header**:
   ```
   X-Site: site1
   ```

2. **X-Site-ID Header**:
   ```
   X-Site-ID: site2
   ```

3. **site Query Parameter**:
   ```
   GET /api/endpoint?site=site3
   ```

If no site is specified, the default client secret is used.

### Authentication Methods

For requests from external sources (non-localhost), you must provide the appropriate client secret using one of the following methods:

1. **Authorization Header** (recommended):
   ```
   Authorization: Bearer your-client-secret
   ```

2. **Custom Header**:
   ```
   X-Client-Secret: your-client-secret
   ```

3. **Query Parameter**:
   ```
   GET /api/endpoint?client_secret=your-client-secret
   ```

### Localhost Exemption

Requests from localhost (127.0.0.1, ::1) are automatically exempted from client secret validation. This includes:
- Direct requests to 127.0.0.1
- Requests with X-Forwarded-For or X-Real-IP headers indicating localhost

### Example Usage

```bash
# Localhost request (no auth required)
curl http://localhost:8080/

# External request with default client secret
curl -H "Authorization: Bearer your-default-client-secret-here" http://your-server.com/

# Site1 request with site-specific secret
curl -H "X-Site: site1" -H "X-Client-Secret: site1-secret-key-12345" http://your-server.com/

# Site2 request with Bearer token
curl -H "X-Site: site2" -H "Authorization: Bearer site2-secret-key-67890" http://your-server.com/

# Site3 request with query parameters
curl "http://your-server.com/?site=site3&client_secret=site3-secret-key-abcde"

# Unknown site uses default secret
curl -H "X-Site: unknown_site" -H "X-Client-Secret: your-default-client-secret-here" http://your-server.com/
```

### Security Behavior

- **Site-specific requests**: If a site is specified (e.g., `site1`), the request must use the corresponding site-specific secret
- **Default requests**: If no site is specified or the site is unknown, the default client secret is used
- **Localhost exemption**: All localhost requests bypass authentication regardless of site
- **Logging**: All authentication attempts are logged with site information for auditing

### Testing

Run the security tests to verify the authentication:

```bash
pytest tests/test_security.py -v
```

