"""
Admin authentication module for the system admin console.
Uses a secret code stored in environment variable for authentication.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib

# Store active admin sessions (in production, use Redis or similar)
admin_sessions = {}

# Session timeout in minutes
SESSION_TIMEOUT_MINUTES = 30


def get_admin_secret() -> str:
    """
    Get the admin secret code from environment variable.
    Default secret for development: 'admin-secret-2026'
    In production, set the ADMIN_SECRET_CODE environment variable.
    """
    return os.environ.get("ADMIN_SECRET_CODE", "admin-secret-2026")


def verify_admin_code(code: str) -> bool:
    """Verify if the provided code matches the admin secret."""
    return code == get_admin_secret()


def create_admin_session() -> str:
    """Create a new admin session and return the session token."""
    session_token = secrets.token_urlsafe(32)
    admin_sessions[session_token] = {
        "created_at": datetime.now(),
        "last_activity": datetime.now()
    }
    return session_token


def verify_admin_session(session_token: str) -> bool:
    """Verify if the session token is valid and not expired."""
    if session_token not in admin_sessions:
        return False
    
    session = admin_sessions[session_token]
    last_activity = session["last_activity"]
    
    # Check if session has expired
    if datetime.now() - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        # Remove expired session
        del admin_sessions[session_token]
        return False
    
    # Update last activity time
    admin_sessions[session_token]["last_activity"] = datetime.now()
    return True


def invalidate_admin_session(session_token: str) -> None:
    """Invalidate an admin session (logout)."""
    if session_token in admin_sessions:
        del admin_sessions[session_token]


def cleanup_expired_sessions() -> None:
    """Remove all expired sessions."""
    now = datetime.now()
    expired_tokens = [
        token for token, session in admin_sessions.items()
        if now - session["last_activity"] > timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    ]
    for token in expired_tokens:
        del admin_sessions[token]
