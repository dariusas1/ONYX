"""
Authentication and Authorization Utilities

This module provides authentication and authorization middleware for API endpoints.
Implements session-based and JWT-based authentication for secure access control.
"""

import os
import logging
from typing import Optional
from fastapi import HTTPException, Header, Query
from datetime import datetime, timedelta
import jwt
import secrets

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 24))


def create_jwt_token(user_id: str, email: str) -> str:
    """
    Create a JWT token for user authentication

    Args:
        user_id: User UUID
        email: User email address

    Returns:
        JWT token string
    """
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token: str) -> dict:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


async def get_current_user(
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None),
) -> dict:
    """
    FastAPI dependency to get current authenticated user

    Validates that:
    1. Authorization header contains valid JWT token
    2. User ID from JWT matches user_id parameter (if provided)

    Args:
        authorization: Authorization header (Bearer <token>)
        user_id: User ID from request (optional)

    Returns:
        User information dict with user_id and email

    Raises:
        HTTPException: If authentication fails
    """
    # Check for authorization header
    if not authorization:
        logger.warning("Missing authorization header")
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header. Please provide 'Authorization: Bearer <token>'",
        )

    # Extract token from Bearer scheme
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid authorization header format: {authorization}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
        )

    token = parts[1]

    # Verify token
    payload = verify_jwt_token(token)

    # Extract user information
    token_user_id = payload.get("user_id")
    token_email = payload.get("email")

    if not token_user_id or not token_email:
        logger.error("JWT token missing user_id or email")
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # If user_id is provided in query/path, verify it matches token
    if user_id and user_id != token_user_id:
        logger.warning(
            f"User ID mismatch: token={token_user_id}, requested={user_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only access your own resources",
        )

    return {
        "user_id": token_user_id,
        "email": token_email,
    }


async def require_authenticated_user(
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    Simplified authentication dependency that doesn't check user_id parameter

    Use this for endpoints that don't have user_id in the path/query

    Args:
        authorization: Authorization header (Bearer <token>)

    Returns:
        User information dict

    Raises:
        HTTPException: If authentication fails
    """
    return await get_current_user(authorization=authorization, user_id=None)


def verify_user_access(current_user: dict, requested_user_id: str) -> None:
    """
    Verify that the current user has access to requested_user_id's resources

    Args:
        current_user: Current authenticated user dict
        requested_user_id: User ID being accessed

    Raises:
        HTTPException: If access is denied
    """
    if current_user["user_id"] != requested_user_id:
        logger.warning(
            f"Access denied: user {current_user['user_id']} tried to access {requested_user_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only access your own resources",
        )
