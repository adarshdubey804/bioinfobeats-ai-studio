from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError
from app.core.config import settings

def rate_limit(scope: str, limit: int, window_seconds: int):
    """Redis-backed fixed-window limiter; fail closed if shared state is unavailable."""
    def dependency(request: Request):
        import time
        client = request.client.host if request.client else "unknown"
        key = f"rate:{scope}:{client}:{int(time.time()) // window_seconds}"
        try:
            redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, window_seconds)
        except RedisError:
            raise HTTPException(503, "Rate limiting service is temporarily unavailable.")
        if count > limit:
            raise HTTPException(429, "Too many requests. Please try again later.", headers={"Retry-After": str(window_seconds)})
    return dependency
