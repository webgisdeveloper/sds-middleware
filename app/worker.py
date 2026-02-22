"""
Worker API endpoints for job management.
Handles job creation, status updates, and worker operations.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import pymysql
from datetime import datetime

from app.core.config import settings
from app.core.download_tokens import (
    TokenManager, 
    DownloadToken, 
    TokenStatus,
    SQL_QUERIES
)
from app.core.logger import logger

router = APIRouter(prefix="/worker", tags=["worker"])


class CreateJobRequest(BaseModel):
    """Request model for creating a new job"""
    user_email: EmailStr
    file_name: str


class CreateJobResponse(BaseModel):
    """Response model for job creation"""
    success: bool
    message: str
    job_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


def get_db_connection():
    """Get a database connection using settings"""
    try:
        connection = pymysql.connect(
            host=settings.database.host,
            user=settings.database.user,
            password=settings.database.password,
            database=settings.database.db,
            port=3306,
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )


@router.post("/create_job", response_model=CreateJobResponse)
async def create_job(request: CreateJobRequest):
    """
    Create a new job entry in the user_jobs table.
    
    Args:
        request: CreateJobRequest with user_email and file_name
    
    Returns:
        CreateJobResponse with job creation details
    """
    connection = None
    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            # Insert new job with submitted status
            sql = """
                INSERT INTO user_jobs (user_email, file_name, job_status, created_time)
                VALUES (%s, %s, %s, %s)
            """
            created_time = datetime.now()
            cursor.execute(sql, (
                request.user_email,
                request.file_name,
                'submitted',
                created_time
            ))
            
            # Get the inserted job_id
            job_id = cursor.lastrowid
            
            connection.commit()
            
            return CreateJobResponse(
                success=True,
                message="Job created successfully",
                job_id=job_id,
                details={
                    "user_email": request.user_email,
                    "file_name": request.file_name,
                    "job_status": "submitted",
                    "created_time": created_time.isoformat()
                }
            )
            
    except pymysql.MySQLError as e:
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating job: {str(e)}"
        )
    finally:
        if connection:
            connection.close()


class GenerateTokenRequest(BaseModel):
    """Request model for generating a download token"""
    job_id: int
    user_email: EmailStr
    max_downloads: int = 3
    expiry_hours: int = 24


class GenerateTokenResponse(BaseModel):
    """Response model for token generation"""
    success: bool
    token: Optional[str] = None
    expires_at: Optional[str] = None
    max_downloads: int
    message: str


class ValidateTokenResponse(BaseModel):
    """Response model for token validation"""
    valid: bool
    token_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@router.post("/generate_token", response_model=GenerateTokenResponse)
async def generate_download_token(request: GenerateTokenRequest):
    """
    Generate a new download token for a completed job.
    Token expires after 24 hours or 3 downloads by default.
    
    Args:
        request: GenerateTokenRequest with job_id, user_email, and optional limits
    
    Returns:
        GenerateTokenResponse with token details
    """
    connection = None
    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            # Verify job exists and belongs to user
            cursor.execute(
                "SELECT job_id, user_email, job_status FROM user_jobs WHERE job_id = %s",
                (request.job_id,)
            )
            job = cursor.fetchone()
            
            if not job:
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {request.job_id} not found"
                )
            
            if job['user_email'] != request.user_email:
                raise HTTPException(
                    status_code=403,
                    detail="Job does not belong to this user"
                )
            
            if job['job_status'] != 'completed':
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot generate token for job with status: {job['job_status']}"
                )
            
            # Generate token data
            token_data = TokenManager.create_token_data(
                job_id=request.job_id,
                user_email=request.user_email,
                max_downloads=request.max_downloads,
                expiry_hours=request.expiry_hours
            )
            
            # Insert token into database
            cursor.execute(SQL_QUERIES['create_token'], token_data)
            connection.commit()
            
            logger.info(
                f"Generated download token for job {request.job_id}, "
                f"expires at {token_data['expires_at']}"
            )
            
            return GenerateTokenResponse(
                success=True,
                token=token_data['token'],
                expires_at=token_data['expires_at'].isoformat(),
                max_downloads=token_data['max_downloads'],
                message="Download token generated successfully"
            )
            
    except HTTPException:
        raise
    except pymysql.MySQLError as e:
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating token: {str(e)}"
        )
    finally:
        if connection:
            connection.close()


@router.get("/validate_token/{token}", response_model=ValidateTokenResponse)
async def validate_download_token(token: str, request: Request):
    """
    Validate a download token and return its details.
    Checks expiration time and download count.
    
    Args:
        token: Download token string
        request: FastAPI request object for client IP
    
    Returns:
        ValidateTokenResponse with validation result
    """
    connection = None
    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            # Get token from database
            cursor.execute(SQL_QUERIES['get_token'], {'token': token})
            token_row = cursor.fetchone()
            
            if not token_row:
                return ValidateTokenResponse(
                    valid=False,
                    error_message="Token not found"
                )
            
            # Create DownloadToken object
            download_token = DownloadToken(**token_row)
            
            # Validate token
            is_valid, error_msg = TokenManager.validate_token_params(
                download_token,
                client_ip=request.client.host if request.client else None
            )
            
            if not is_valid:
                # Mark token as expired if it should be
                if download_token.should_expire():
                    cursor.execute(
                        SQL_QUERIES['mark_expired'],
                        {'token_id': download_token.token_id}
                    )
                    connection.commit()
                    logger.info(f"Marked token {token} as expired")
                
                return ValidateTokenResponse(
                    valid=False,
                    token_info=download_token.to_dict(),
                    error_message=error_msg
                )
            
            return ValidateTokenResponse(
                valid=True,
                token_info=download_token.to_dict()
            )
            
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating token: {str(e)}"
        )
    finally:
        if connection:
            connection.close()


@router.post("/record_download/{token}")
async def record_download(token: str, request: Request):
    """
    Record a download event for a token.
    Increments download count and updates last download time/IP.
    
    Args:
        token: Download token string
        request: FastAPI request object for client IP
    
    Returns:
        Download confirmation with updated token info
    """
    connection = None
    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            # Get and validate token
            cursor.execute(SQL_QUERIES['get_token'], {'token': token})
            token_row = cursor.fetchone()
            
            if not token_row:
                raise HTTPException(
                    status_code=404,
                    detail="Token not found"
                )
            
            download_token = DownloadToken(**token_row)
            
            # Validate token before recording download
            is_valid, error_msg = TokenManager.validate_token_params(
                download_token,
                client_ip=request.client.host if request.client else None
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=403,
                    detail=error_msg or "Token is invalid"
                )
            
            # Record download
            client_ip = request.client.host if request.client else None
            update_data = TokenManager.prepare_download_update(
                token_id=download_token.token_id,
                client_ip=client_ip
            )
            
            cursor.execute(SQL_QUERIES['update_download'], update_data)
            
            # Check if token should be expired after this download
            new_count = download_token.download_count + 1
            if new_count >= download_token.max_downloads:
                cursor.execute(
                    SQL_QUERIES['mark_expired'],
                    {'token_id': download_token.token_id}
                )
                logger.info(
                    f"Token {token} marked as expired after {new_count} downloads"
                )
            
            connection.commit()
            
            logger.info(
                f"Recorded download for token {token} "
                f"(count: {new_count}/{download_token.max_downloads}) "
                f"from IP: {client_ip}"
            )
            
            return {
                "success": True,
                "message": "Download recorded successfully",
                "download_count": new_count,
                "max_downloads": download_token.max_downloads,
                "remaining_downloads": max(0, download_token.max_downloads - new_count),
                "job_id": download_token.job_id
            }
            
    except HTTPException:
        raise
    except pymysql.MySQLError as e:
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error recording download: {str(e)}"
        )
    finally:
        if connection:
            connection.close()


@router.post("/expire_old_tokens")
async def expire_old_tokens():
    """
    Batch update to mark expired tokens.
    Marks tokens as expired if they've passed 24 hours or reached max downloads.
    
    Returns:
        Count of expired tokens
    """
    connection = None
    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            cursor.execute(SQL_QUERIES['expire_old_tokens'])
            expired_count = cursor.rowcount
            connection.commit()
            
            logger.info(f"Marked {expired_count} tokens as expired")
            
            return {
                "success": True,
                "expired_count": expired_count,
                "message": f"Marked {expired_count} tokens as expired"
            }
            
    except pymysql.MySQLError as e:
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error expiring tokens: {str(e)}"
        )
    finally:
        if connection:
            connection.close()


@router.get("/job/{job_id}/tokens")
async def get_job_tokens(job_id: int, user_email: EmailStr):
    """
    Get all tokens associated with a job.
    
    Args:
        job_id: Job ID
        user_email: User email for authorization
    
    Returns:
        List of tokens for the job
    """
    connection = None
    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            # Verify job belongs to user
            cursor.execute(
                "SELECT user_email FROM user_jobs WHERE job_id = %s",
                (job_id,)
            )
            job = cursor.fetchone()
            
            if not job:
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {job_id} not found"
                )
            
            if job['user_email'] != user_email:
                raise HTTPException(
                    status_code=403,
                    detail="Job does not belong to this user"
                )
            
            # Get all tokens for the job
            cursor.execute(SQL_QUERIES['get_job_tokens'], {'job_id': job_id})
            tokens = cursor.fetchall()
            
            # Convert to DownloadToken objects and serialize
            token_list = [
                DownloadToken(**token_row).to_dict()
                for token_row in tokens
            ]
            
            return {
                "success": True,
                "job_id": job_id,
                "token_count": len(token_list),
                "tokens": token_list
            }
            
    except HTTPException:
        raise
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tokens: {str(e)}"
        )
    finally:
        if connection:
            connection.close()
