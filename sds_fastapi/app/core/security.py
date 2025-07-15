import ipaddress
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.config import settings
from app.core.logger import logger


class ClientSecretMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate client secret for all API calls except those from localhost.
    """
    
    def __init__(self, app, client_secret: str):
        super().__init__(app)
        self.client_secret = client_secret
        self.localhost_ips = {
            ipaddress.ip_address("127.0.0.1"),
            ipaddress.ip_address("::1"),
        }
    
    def is_localhost(self, ip: str) -> bool:
        """Check if the request comes from localhost."""
        try:
            client_ip = ipaddress.ip_address(ip)
            return client_ip in self.localhost_ips
        except ValueError:
            return False
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxy headers."""
        # Check for X-Forwarded-For header (common with reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        # Check for X-Real-IP header (common with nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def validate_client_secret(self, request: Request) -> bool:
        """Validate client secret from headers."""
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            return token == self.client_secret
        
        # Check X-Client-Secret header
        client_secret_header = request.headers.get("X-Client-Secret")
        if client_secret_header:
            return client_secret_header == self.client_secret
        
        # Check query parameter
        client_secret_param = request.query_params.get("client_secret")
        if client_secret_param:
            return client_secret_param == self.client_secret
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Skip validation for localhost
        if self.is_localhost(client_ip):
            logger.info(f"Localhost request from {client_ip}, skipping client secret validation")
            response = await call_next(request)
            return response
        
        # Validate client secret for non-localhost requests
        if not self.validate_client_secret(request):
            logger.warning(f"Unauthorized request from {client_ip} - missing or invalid client secret")
            return Response(
                content='{"detail": "Missing or invalid client secret"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
        
        logger.info(f"Authorized request from {client_ip}")
        response = await call_next(request)
        return response


def add_security_middleware(app):
    """Add client secret security middleware to the FastAPI app."""
    app.add_middleware(
        ClientSecretMiddleware,
        client_secret=settings.webserver.client_secret
    )
