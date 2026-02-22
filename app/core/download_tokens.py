"""
Download token management module.

Handles creation, validation, and expiration of download tokens with
24-hour expiration and 3-download limit.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
import secrets
import hashlib
from app.core.logger import logger


class TokenStatus(str, Enum):
    """Token status enumeration."""
    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"


class DownloadToken:
    """
    Download token model with validation logic.
    
    A token expires when:
    - 24 hours have passed since creation
    - Download count reaches or exceeds max_downloads (default: 3)
    """
    
    def __init__(
        self,
        token_id: int,
        token: str,
        job_id: int,
        status: str,
        download_count: int,
        max_downloads: int,
        created_time: datetime,
        expires_at: datetime,
        last_download_time: Optional[datetime] = None,
        last_download_ip: Optional[str] = None
    ):
        self.token_id = token_id
        self.token = token
        self.job_id = job_id
        self.status = TokenStatus(status)
        self.download_count = download_count
        self.max_downloads = max_downloads
        self.created_time = created_time
        self.expires_at = expires_at
        self.last_download_time = last_download_time
        self.last_download_ip = last_download_ip
    
    def is_valid(self) -> bool:
        """Check if token is valid for download."""
        # Check status
        if self.status != TokenStatus.ACTIVE:
            logger.debug(f"Token {self.token} is not active (status: {self.status})")
            return False
        
        # Check time expiration
        if datetime.now() >= self.expires_at:
            logger.debug(f"Token {self.token} has expired (expires_at: {self.expires_at})")
            return False
        
        # Check download count
        if self.download_count >= self.max_downloads:
            logger.debug(
                f"Token {self.token} has reached max downloads "
                f"({self.download_count}/{self.max_downloads})"
            )
            return False
        
        return True
    
    def should_expire(self) -> bool:
        """Determine if token should be marked as expired."""
        return (
            datetime.now() >= self.expires_at or 
            self.download_count >= self.max_downloads
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary."""
        return {
            "token_id": self.token_id,
            "token": self.token,
            "job_id": self.job_id,
            "status": self.status.value,
            "download_count": self.download_count,
            "max_downloads": self.max_downloads,
            "created_time": self.created_time.isoformat() if self.created_time else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_download_time": self.last_download_time.isoformat() if self.last_download_time else None,
            "last_download_ip": self.last_download_ip,
            "is_valid": self.is_valid(),
            "remaining_downloads": max(0, self.max_downloads - self.download_count)
        }


class TokenManager:
    """Manager for download token operations."""
    
    @staticmethod
    def generate_token(job_id: int, user_email: str) -> str:
        """
        Generate a secure random token.
        
        Creates a 32-character hex token using secrets module for cryptographic security.
        """
        random_bytes = secrets.token_bytes(16)
        timestamp = str(datetime.now().timestamp())
        data = f"{job_id}:{user_email}:{timestamp}:{random_bytes.hex()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    @staticmethod
    def create_token_data(
        job_id: int,
        user_email: str,
        max_downloads: int = 3,
        expiry_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Create token data for database insertion.
        
        Args:
            job_id: Job ID to associate with token
            user_email: User email for token generation
            max_downloads: Maximum number of downloads allowed (default: 3)
            expiry_hours: Hours until token expires (default: 24)
            
        Returns:
            Dictionary with token data ready for database insertion
        """
        now = datetime.now()
        token = TokenManager.generate_token(job_id, user_email)
        expires_at = now + timedelta(hours=expiry_hours)
        
        return {
            "token": token,
            "job_id": job_id,
            "status": TokenStatus.ACTIVE.value,
            "download_count": 0,
            "max_downloads": max_downloads,
            "created_time": now,
            "expires_at": expires_at
        }
    
    @staticmethod
    def validate_token_params(
        token: DownloadToken,
        client_ip: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate token for download.
        
        Args:
            token: DownloadToken object to validate
            client_ip: Optional client IP for logging
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not token.is_valid():
            if token.status != TokenStatus.ACTIVE:
                return False, f"Token is {token.status.value}"
            elif datetime.now() >= token.expires_at:
                return False, "Token has expired (24 hours elapsed)"
            elif token.download_count >= token.max_downloads:
                return False, f"Token has reached maximum downloads ({token.max_downloads})"
            else:
                return False, "Token is invalid"
        
        return True, None
    
    @staticmethod
    def prepare_download_update(
        token_id: int,
        client_ip: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare data for updating token after download.
        
        Args:
            token_id: Token ID to update
            client_ip: Optional client IP to record
            
        Returns:
            Dictionary with update data
        """
        update_data = {
            "token_id": token_id,
            "download_count_increment": 1,
            "last_download_time": datetime.now(),
            "last_download_ip": client_ip
        }
        
        return update_data


# Example SQL queries for token operations
SQL_QUERIES = {
    "create_token": """
        INSERT INTO download_tokens 
        (token, job_id, status, download_count, max_downloads, created_time, expires_at)
        VALUES (%(token)s, %(job_id)s, %(status)s, %(download_count)s, 
                %(max_downloads)s, %(created_time)s, %(expires_at)s)
    """,
    
    "get_token": """
        SELECT token_id, token, job_id, status, download_count, max_downloads,
               created_time, expires_at, last_download_time, last_download_ip
        FROM download_tokens
        WHERE token = %(token)s
    """,
    
    "update_download": """
        UPDATE download_tokens
        SET download_count = download_count + 1,
            last_download_time = %(last_download_time)s,
            last_download_ip = %(last_download_ip)s
        WHERE token_id = %(token_id)s
    """,
    
    "mark_expired": """
        UPDATE download_tokens
        SET status = 'expired'
        WHERE token_id = %(token_id)s
    """,
    
    "expire_old_tokens": """
        UPDATE download_tokens
        SET status = 'expired'
        WHERE status = 'active' 
        AND (expires_at < NOW() OR download_count >= max_downloads)
    """,
    
    "disable_token": """
        UPDATE download_tokens
        SET status = 'disabled'
        WHERE token = %(token)s
    """,
    
    "get_job_tokens": """
        SELECT token_id, token, job_id, status, download_count, max_downloads,
               created_time, expires_at, last_download_time, last_download_ip
        FROM download_tokens
        WHERE job_id = %(job_id)s
        ORDER BY created_time DESC
    """
}
