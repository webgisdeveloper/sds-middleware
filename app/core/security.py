import ipaddress
from typing import Optional, Dict
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.config import settings
from app.core.logger import logger


class ClientSecretMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate client secret for all API calls except those from localhost.
    Supports site-specific client secrets based on request headers.
    """
    
    def __init__(self, app, default_client_secret: str, site_secrets: Dict[str, str]):
        super().__init__(app)
        self.default_client_secret = default_client_secret
        self.site_secrets = site_secrets
        self.localhost_ips = {
            ipaddress.ip_address("127.0.0.1"),
            ipaddress.ip_address("::1"),
        }
    
    def get_site_from_request(self, request: Request) -> Optional[str]:
        """Extract site identifier from request headers."""
        # Check for X-Site header
        site_header = request.headers.get("X-Site")
        if site_header:
            return site_header.lower()
        
        # Check for X-Site-ID header (alternative)
        site_id_header = request.headers.get("X-Site-ID")
        if site_id_header:
            return site_id_header.lower()
        
        # Check for site query parameter
        site_param = request.query_params.get("site")
        if site_param:
            return site_param.lower()
        
        return None
    
    def get_expected_client_secret(self, site: Optional[str]) -> str:
        """Get the expected client secret for a given site."""
        if site and site in self.site_secrets:
            return self.site_secrets[site]
        return self.default_client_secret
    
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
        """Validate client secret from headers, using site-specific secret if available."""
        site = self.get_site_from_request(request)
        expected_secret = self.get_expected_client_secret(site)
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            return token == expected_secret
        
        # Check X-Client-Secret header
        client_secret_header = request.headers.get("X-Client-Secret")
        if client_secret_header:
            return client_secret_header == expected_secret
        
        # Check query parameter
        client_secret_param = request.query_params.get("client_secret")
        if client_secret_param:
            return client_secret_param == expected_secret
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP and site
        client_ip = self.get_client_ip(request)
        site = self.get_site_from_request(request)
        
        # Skip validation for localhost
        if self.is_localhost(client_ip):
            site_info = f" for site '{site}'" if site else ""
            logger.info(f"Localhost request from {client_ip}{site_info}, skipping client secret validation")
            response = await call_next(request)
            return response
        
        # Validate client secret for non-localhost requests
        if not self.validate_client_secret(request):
            site_info = f" for site '{site}'" if site else ""
            logger.warning(f"Unauthorized request from {client_ip}{site_info} - missing or invalid client secret")
            return Response(
                content='{"detail": "Missing or invalid client secret"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
        
        site_info = f" for site '{site}'" if site else ""
        logger.info(f"Authorized request from {client_ip}{site_info}")
        response = await call_next(request)
        return response


def add_security_middleware(app):
    """Add client secret security middleware to the FastAPI app."""
    app.add_middleware(
        ClientSecretMiddleware,
        default_client_secret=settings.webserver.client_secret,
        site_secrets=settings.webserver.site_secrets
    )
