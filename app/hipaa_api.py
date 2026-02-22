"""
HIPAA API Endpoints for JWT Encryption/Decryption

Provides secure API endpoints for creating and validating encrypted JWT tokens
for worker API authentication and data access with HIPAA compliance.
"""

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import settings
from app.core.hipaa_jwt import (
    get_jwt_manager,
    TokenPurpose,
    HIPAAJWTManager
)
from app.core.logger import logger


router = APIRouter(prefix="/hipaa", tags=["hipaa"])


# ============================================================
# Request/Response Models
# ============================================================

class CreateTokenRequest(BaseModel):
    """Request model for creating encrypted JWT token"""
    payload: Dict[str, Any] = Field(..., description="Data to encrypt in token")
    purpose: TokenPurpose = Field(..., description="Token purpose (worker_auth, data_access, file_download, admin_access)")
    user_id: Optional[str] = Field(None, description="User identifier for audit trail")
    expiry_hours: Optional[int] = Field(24, ge=1, le=168, description="Token expiration in hours (1-168, default: 24)")
    
    class Config:
        schema_extra = {
            "example": {
                "payload": {
                    "worker_id": "worker-123",
                    "permissions": ["read", "write"],
                    "data_scope": "clinical_records"
                },
                "purpose": "worker_auth",
                "user_id": "admin@example.com",
                "expiry_hours": 24
            }
        }


class CreateTokenResponse(BaseModel):
    """Response model for token creation"""
    success: bool
    token: str = Field(..., description="Encrypted JWT token")
    token_id: str = Field(..., description="Unique token identifier for tracking")
    expires_at: str = Field(..., description="Token expiration timestamp (ISO 8601)")
    purpose: str
    message: str


class ValidateTokenRequest(BaseModel):
    """Request model for token validation"""
    token: str = Field(..., description="JWT token to validate and decrypt")
    expected_purpose: Optional[TokenPurpose] = Field(None, description="Expected token purpose for validation")
    
    class Config:
        schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expected_purpose": "worker_auth"
            }
        }


class ValidateTokenResponse(BaseModel):
    """Response model for token validation"""
    valid: bool
    payload: Optional[Dict[str, Any]] = Field(None, description="Decrypted payload data")
    token_metadata: Optional[Dict[str, Any]] = Field(None, description="Token metadata (ID, purpose, timestamps)")
    error_message: Optional[str] = None


class TokenInfoResponse(BaseModel):
    """Response model for token information"""
    token_id: str
    purpose: str
    user_id: Optional[str]
    issued_at: str
    expires_at: str
    is_revoked: bool


class RevokeTokenRequest(BaseModel):
    """Request model for token revocation"""
    token_id: str = Field(..., description="Token ID to revoke")
    reason: Optional[str] = Field(None, description="Reason for revocation")


class RevokeTokenResponse(BaseModel):
    """Response model for token revocation"""
    success: bool
    token_id: str
    message: str


# ============================================================
# Helper Functions
# ============================================================

def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    if request.client:
        return request.client.host
    
    return "unknown"


def initialize_jwt_manager() -> HIPAAJWTManager:
    """Initialize JWT manager with configuration."""
    try:
        # Use webserver client_secret as JWT secret
        jwt_secret = settings.webserver.client_secret
        
        # Use a dedicated encryption key if available, otherwise derive from secret
        encryption_key = getattr(settings.webserver, 'jwt_encryption_key', jwt_secret)
        
        return get_jwt_manager(
            secret_key=jwt_secret,
            encryption_key=encryption_key
        )
    except Exception as e:
        logger.error(f"Failed to initialize JWT manager: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT manager initialization failed"
        )


# ============================================================
# API Endpoints
# ============================================================

@router.post("/create_token", response_model=CreateTokenResponse)
async def create_encrypted_token(request: CreateTokenRequest, http_request: Request):
    """
    Create an encrypted JWT token with HIPAA-compliant audit logging.
    
    **Security Features:**
    - AES-256 encryption of payload data
    - JWT signature for integrity verification
    - Automatic expiration (default: 24 hours)
    - Audit logging for HIPAA compliance
    - Unique token ID for tracking
    
    **Use Cases:**
    - Worker API authentication
    - Secure data access tokens
    - File download authorization
    - Admin operations
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/hipaa/create_token \\
      -H "Content-Type: application/json" \\
      -d '{
        "payload": {"worker_id": "w123", "permissions": ["read"]},
        "purpose": "worker_auth",
        "user_id": "admin@example.com",
        "expiry_hours": 24
      }'
    ```
    """
    try:
        jwt_manager = initialize_jwt_manager()
        client_ip = get_client_ip(http_request)
        
        # Create encrypted token
        token, token_id = jwt_manager.create_encrypted_token(
            payload=request.payload,
            purpose=request.purpose,
            user_id=request.user_id,
            ip_address=client_ip,
            expiry_hours=request.expiry_hours
        )
        
        # Calculate expiration timestamp
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(hours=request.expiry_hours or 24)
        
        logger.info(
            f"Created HIPAA JWT token {token_id} for user {request.user_id} "
            f"from IP {client_ip}, purpose: {request.purpose.value}"
        )
        
        return CreateTokenResponse(
            success=True,
            token=token,
            token_id=token_id,
            expires_at=expires_at.isoformat() + "Z",
            purpose=request.purpose.value,
            message="Token created successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to create token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token creation failed: {str(e)}"
        )


@router.post("/validate_token", response_model=ValidateTokenResponse)
async def validate_and_decrypt_token(request: ValidateTokenRequest, http_request: Request):
    """
    Validate and decrypt an encrypted JWT token with HIPAA audit logging.
    
    **Validation Checks:**
    - Token signature verification
    - Expiration check
    - Revocation status check
    - Purpose validation (if specified)
    - Payload decryption
    
    **Returns:**
    - Decrypted payload data
    - Token metadata (ID, purpose, timestamps)
    - Validation status and error messages
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/hipaa/validate_token \\
      -H "Content-Type: application/json" \\
      -d '{
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expected_purpose": "worker_auth"
      }'
    ```
    """
    try:
        jwt_manager = initialize_jwt_manager()
        client_ip = get_client_ip(http_request)
        
        # Validate and decrypt token
        is_valid, decrypted_payload, error_message = jwt_manager.validate_and_decrypt_token(
            token=request.token,
            purpose=request.expected_purpose,
            ip_address=client_ip
        )
        
        if not is_valid:
            logger.warning(
                f"Token validation failed from IP {client_ip}: {error_message}"
            )
            return ValidateTokenResponse(
                valid=False,
                error_message=error_message
            )
        
        # Extract metadata
        token_metadata = decrypted_payload.pop("_token_metadata", {})
        
        logger.info(
            f"Validated token {token_metadata.get('token_id')} from IP {client_ip}"
        )
        
        return ValidateTokenResponse(
            valid=True,
            payload=decrypted_payload,
            token_metadata=token_metadata
        )
        
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token validation failed: {str(e)}"
        )


@router.get("/token_info/{token}", response_model=TokenInfoResponse)
async def get_token_information(token: str, http_request: Request):
    """
    Get token metadata without full validation (inspection mode).
    
    **Use Case:** Check token details without consuming it or full validation.
    
    **Note:** This endpoint does NOT validate the token signature or expiration.
    Use `validate_token` endpoint for full validation.
    
    **Example:**
    ```bash
    curl http://localhost:8000/hipaa/token_info/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```
    """
    try:
        jwt_manager = initialize_jwt_manager()
        
        token_info = jwt_manager.get_token_info(token)
        
        if not token_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot extract token information"
            )
        
        return TokenInfoResponse(**token_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get token info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve token information: {str(e)}"
        )


@router.post("/revoke_token", response_model=RevokeTokenResponse)
async def revoke_token(request: RevokeTokenRequest, http_request: Request):
    """
    Revoke a token (add to revocation list).
    
    **Effect:** Token will fail validation even if not expired.
    
    **Use Cases:**
    - User logout
    - Security breach response
    - Access revocation
    - Token compromise
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/hipaa/revoke_token \\
      -H "Content-Type: application/json" \\
      -d '{
        "token_id": "abc123xyz",
        "reason": "User logout"
      }'
    ```
    """
    try:
        jwt_manager = initialize_jwt_manager()
        client_ip = get_client_ip(http_request)
        
        # Revoke token
        jwt_manager.revoke_token(
            token_id=request.token_id,
            ip_address=client_ip
        )
        
        logger.info(
            f"Token {request.token_id} revoked from IP {client_ip}. "
            f"Reason: {request.reason or 'Not specified'}"
        )
        
        return RevokeTokenResponse(
            success=True,
            token_id=request.token_id,
            message=f"Token {request.token_id} has been revoked"
        )
        
    except Exception as e:
        logger.error(f"Failed to revoke token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token revocation failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for HIPAA API.
    
    **Returns:** API status and JWT manager availability.
    """
    try:
        jwt_manager = initialize_jwt_manager()
        return {
            "status": "healthy",
            "service": "HIPAA JWT API",
            "jwt_manager": "initialized",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "HIPAA JWT API",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


# ============================================================
# Worker-Specific Convenience Endpoints
# ============================================================

@router.post("/worker/authenticate")
async def authenticate_worker(
    worker_id: str,
    permissions: List[str],
    user_email: Optional[EmailStr] = None,
    expiry_hours: int = 24,
    http_request: Request = None
):
    """
    Convenience endpoint to create worker authentication token.
    
    **Simplified API** for creating worker auth tokens without manual payload construction.
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/hipaa/worker/authenticate?worker_id=w123&permissions=read&permissions=write&expiry_hours=24"
    ```
    """
    try:
        jwt_manager = initialize_jwt_manager()
        client_ip = get_client_ip(http_request)
        
        payload = {
            "worker_id": worker_id,
            "permissions": permissions,
            "authenticated_at": datetime.utcnow().isoformat()
        }
        
        token, token_id = jwt_manager.create_encrypted_token(
            payload=payload,
            purpose=TokenPurpose.WORKER_AUTH,
            user_id=user_email or worker_id,
            ip_address=client_ip,
            expiry_hours=expiry_hours
        )
        
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        return {
            "success": True,
            "token": token,
            "token_id": token_id,
            "worker_id": worker_id,
            "permissions": permissions,
            "expires_at": expires_at.isoformat() + "Z",
            "message": f"Worker {worker_id} authenticated successfully"
        }
        
    except Exception as e:
        logger.error(f"Worker authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Worker authentication failed: {str(e)}"
        )


@router.post("/worker/verify")
async def verify_worker_token(
    token: str,
    http_request: Request
):
    """
    Convenience endpoint to verify worker authentication token.
    
    **Simplified API** for validating worker auth tokens.
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/hipaa/worker/verify" \\
      -H "Content-Type: application/json" \\
      -d '{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
    ```
    """
    try:
        jwt_manager = initialize_jwt_manager()
        client_ip = get_client_ip(http_request)
        
        is_valid, decrypted_payload, error_message = jwt_manager.validate_and_decrypt_token(
            token=token,
            purpose=TokenPurpose.WORKER_AUTH,
            ip_address=client_ip
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message or "Token validation failed"
            )
        
        token_metadata = decrypted_payload.pop("_token_metadata", {})
        
        return {
            "valid": True,
            "worker_id": decrypted_payload.get("worker_id"),
            "permissions": decrypted_payload.get("permissions", []),
            "authenticated_at": decrypted_payload.get("authenticated_at"),
            "token_id": token_metadata.get("token_id"),
            "expires_at": token_metadata.get("expires_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Worker token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        )
