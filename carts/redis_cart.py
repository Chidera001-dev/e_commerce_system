import json
import redis

REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_DB = 0

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

def get_cart(key, ttl=86400):
    """
    Retrieve cart from Redis.
    'key' = session key (guest) OR user:{id} (authenticated)
    Automatically extends TTL (sliding expiration).
    """
    redis_key = f"cart:{key}"
    data = r.get(redis_key)

    if not data:
        return {}

    try:
        cart = json.loads(data)
    except json.JSONDecodeError:
        # Corrupt cache → delete it and return empty cart
        r.delete(redis_key)
        return {}

    # Sliding expiration: refresh TTL on access
    r.expire(redis_key, ttl)
    return cart


def save_cart(key, cart_data, ttl=86400):
    """
    Save the cart back to Redis.
    Overwrites existing cart.
    """
    redis_key = f"cart:{key}"
    try:
        r.setex(redis_key, ttl, json.dumps(cart_data))
    except TypeError:
        """
        If someone accidentally passes a non-serializable value,
        fail silently and ensure app doesn't crash.
        """
        r.delete(redis_key)


def clear_cart(key):
    """
    Remove the cart completely from Redis.
    """
    redis_key = f"cart:{key}"
    r.delete(redis_key)


