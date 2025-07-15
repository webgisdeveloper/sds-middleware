# SDS Middleware with FastAPI

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

