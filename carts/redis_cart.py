import json
import redis

REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_DB = 0

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

def get_cart(session_or_user_key):
    data = r.get(f"cart:{session_or_user_key}")
    return json.loads(data) if data else {}

def save_cart(session_or_user_key, cart_data, ttl=86400):
    r.setex(f"cart:{session_or_user_key}", ttl, json.dumps(cart_data))

def clear_cart(session_or_user_key):
    r.delete(f"cart:{session_or_user_key}")
