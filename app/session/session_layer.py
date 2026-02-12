"""
Session layer - Redis-based token store and validation.
"""
from typing import Optional, Dict, Any
import logging
import json
import redis

logger = logging.getLogger(__name__)

# Redis connection pool and client
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None
_session_ttl: int = 86400


def init_redis(host: str, port: int, db: int, session_ttl: int = 86400) -> None:
    """Initialize Redis connection pool. Call once at app startup."""
    global _redis_pool, _redis_client, _session_ttl
    _redis_pool = redis.ConnectionPool(
        host=host,
        port=port,
        db=db,
        decode_responses=True,
        max_connections=10
    )
    _redis_client = redis.Redis(connection_pool=_redis_pool)
    _session_ttl = session_ttl
    logger.info(f"Redis initialized: {host}:{port}/{db}, TTL: {session_ttl}s")


def _get_redis_client() -> redis.Redis:
    """Get Redis client. Raises if not initialized."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_client


def create_session(token: str, user_data: Dict[str, Any]) -> None:
    """Store token and user data in Redis session with TTL."""
    client = _get_redis_client()
    session_key = f"session:{token}"
    client.setex(session_key, _session_ttl, json.dumps(user_data))
    logger.info(f"Session created for user: {user_data.get('email')}")


def get_session(token: str) -> Optional[Dict[str, Any]]:
    """Get user data from Redis session if token exists."""
    client = _get_redis_client()
    session_key = f"session:{token}"
    data = client.get(session_key)
    if data:
        return json.loads(data)
    return None


def remove_session(token: str) -> bool:
    """Remove token from Redis session (logout)."""
    client = _get_redis_client()
    session_key = f"session:{token}"
    result = client.delete(session_key)
    if result > 0:
        logger.info(f"Session removed for token")
        return True
    return False


def is_valid_session(token: str) -> bool:
    """Check if token has valid session in Redis."""
    client = _get_redis_client()
    session_key = f"session:{token}"
    return client.exists(session_key) > 0


def extract_token(auth_header: Optional[str]) -> Optional[str]:
    """Extract JWT token from Authorization header."""
    if not auth_header:
        return None
    
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]
