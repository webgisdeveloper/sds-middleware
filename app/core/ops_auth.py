"""
Operations console authentication module.
Uses a separate secret code for operations personnel.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
import secrets

# Store active operations sessions (in production, use Redis or similar)
ops_sessions = {}

# Session timeout in minutes
SESSION_TIMEOUT_MINUTES = 30


def get_ops_secret() -> str:
    """
    Get the operations secret code from environment variable.
    Default secret for development: 'ops-secret-2026'
    In production, set the OPS_SECRET_CODE environment variable.
    """
    return os.environ.get("OPS_SECRET_CODE", "ops-secret-2026")


def verify_ops_code(code: str) -> bool:
    """Verify if the provided code matches the operations secret."""
    return code == get_ops_secret()


def create_ops_session() -> str:
    """Create a new operations session and return the session token."""
    session_token = secrets.token_urlsafe(32)
    ops_sessions[session_token] = {
        "created_at": datetime.now(),
        "last_activity": datetime.now()
    }
    return session_token


def verify_ops_session(session_token: str) -> bool:
    """Verify if the session token is valid and not expired."""
    if session_token not in ops_sessions:
        return False
    
    session = ops_sessions[session_token]
    last_activity = session["last_activity"]
    
    # Check if session has expired
    if datetime.now() - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        # Remove expired session
        del ops_sessions[session_token]
        return False
    
    # Update last activity time
    ops_sessions[session_token]["last_activity"] = datetime.now()
    return True


def invalidate_ops_session(session_token: str) -> None:
    """Invalidate an operations session (logout)."""
    if session_token in ops_sessions:
        del ops_sessions[session_token]


def cleanup_expired_sessions() -> None:
    """Remove all expired sessions."""
    now = datetime.now()
    expired_tokens = [
        token for token, session in ops_sessions.items()
        if now - session["last_activity"] > timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    ]
    for token in expired_tokens:
        del ops_sessions[token]
