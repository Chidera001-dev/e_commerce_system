import json
import redis

REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_DB = 0

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


def get_cart(key, ttl=86400):
    """
    Retrieve cart from Redis.
    'key' = session key (guest) OR user:{id} (authenticated)
    Returns (cart_data, key) for APIView convenience.
    Automatically refreshes TTL on access.
    """
    redis_key = f"cart:{key}"
    data = r.get(redis_key)

    if not data:
        return {}, key

    try:
        cart = json.loads(data)
        if not isinstance(cart, dict):
            raise ValueError("Cart is not a dict")
    except (json.JSONDecodeError, ValueError):
        r.delete(redis_key)
        return {}, key

    # Sliding expiration
    r.expire(redis_key, ttl)
    return cart, key


def get_cart_raw(key):
    """
    Get raw Redis cart without any APIView processing
    """
    redis_key = f"cart:{key}"
    data = r.get(redis_key)
    if not data:
        return {}
    try:
        cart = json.loads(data)
        if not isinstance(cart, dict):
            raise ValueError("Cart is not a dict")
    except (json.JSONDecodeError, ValueError):
        r.delete(redis_key)
        return {}
    return cart


def save_cart(key, cart_data, ttl=86400):
    """
    Save cart to Redis with TTL.
    Ensures quantities are positive integers and subtotal is recalculated.
    Works for both guest and authenticated cart structures.
    """
    redis_key = f"cart:{key}"

    try:
        # Ensure correct structure
        for pid, item in cart_data.items():
            if not isinstance(item, dict):
                continue
            qty = int(item.get("quantity", 0))
            item["quantity"] = max(qty, 0)
            price = float(item.get("price_snapshot", 0.0))
            item["price_snapshot"] = price
            item["subtotal"] = qty * price

        r.setex(redis_key, ttl, json.dumps(cart_data))
    except (TypeError, ValueError):
        r.delete(redis_key)


def clear_cart(key):
    """
    Remove the cart completely from Redis.
    """
    redis_key = f"cart:{key}"
    r.delete(redis_key)


def update_cart_item(key, product_id, quantity=None, price=None):
    """
    Update an existing item in Redis cart.
    Automatically recalculates subtotal.
    Returns False if item does not exist.
    """
    cart = get_cart(key)[0]  # get cart dict
    pid = str(product_id)

    if pid not in cart:
        return False

    if quantity is not None:
        cart[pid]["quantity"] = max(int(quantity), 0)
    if price is not None:
        cart[pid]["price_snapshot"] = float(price)

    cart[pid]["subtotal"] = cart[pid]["quantity"] * cart[pid]["price_snapshot"]

    save_cart(key, cart)
    return True



