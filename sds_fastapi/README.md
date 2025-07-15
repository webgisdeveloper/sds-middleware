# SDS Middleware with FastAPI

## Security

This application implements client secret authentication for all API calls except those originating from localhost.

### Configuration

Set your client secret in the `app/core/sds.cfg` file:

```ini
[webserver]
client_secret=your-secure-client-secret-here
```

### Authentication Methods

For requests from external sources (non-localhost), you must provide the client secret using one of the following methods:

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

# External request with Bearer token
curl -H "Authorization: Bearer your-client-secret" http://your-server.com/

# External request with custom header
curl -H "X-Client-Secret: your-client-secret" http://your-server.com/

# External request with query parameter
curl "http://your-server.com/?client_secret=your-client-secret"
```

### Testing

Run the security tests to verify the authentication:

```bash
pytest tests/test_security.py -v
```

