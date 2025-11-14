import json
import redis

REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_DB = 0

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

def get_cart(session_or_user_key, ttl=86400):
    """
    Retrieve the cart from Redis.
    Extend TTL each time cart is accessed to implement sliding expiration.
    """
    data = r.get(f"cart:{session_or_user_key}")
    if data:
        # Extend TTL whenever cart is accessed
        r.expire(f"cart:{session_or_user_key}", ttl)
        return json.loads(data)
    return {}

def save_cart(session_or_user_key, cart_data, ttl=86400):
    """
    Save or update the cart in Redis.
    Each save resets TTL automatically.
    """
    r.setex(f"cart:{session_or_user_key}", ttl, json.dumps(cart_data))

def clear_cart(session_or_user_key):
    """
    Remove the cart from Redis.
    """
    r.delete(f"cart:{session_or_user_key}")

