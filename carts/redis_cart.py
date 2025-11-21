import json
import redis

# -------------------- REDIS CONNECTION --------------------
REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_DB = 0

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


# -------------------- GET CART --------------------
def get_cart(key, ttl=86400):
    """
    Retrieve cart from Redis.
    'key' = session key (guest) OR user:{id} (authenticated)
    Automatically extends TTL (sliding expiration).
    Returns an empty dict if no cart exists or cache is corrupted.
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
        # Corrupt cache → delete it and return empty cart
        r.delete(redis_key)
        return {}

    # Sliding expiration: refresh TTL on access
    r.expire(redis_key, ttl)
    return cart


# -------------------- SAVE CART --------------------
def save_cart(key, cart_data, ttl=86400):
    """
    Save the cart back to Redis.
    Overwrites existing cart.
    Ensures quantities are positive integers and subtotal is recalculated.
    """
    redis_key = f"cart:{key}"
    try:
        for pid, item in cart_data.items():
            # Ensure quantity is valid
            qty = int(item.get("quantity", 0))
            if qty < 0:
                qty = 0
            item["quantity"] = qty

            # Ensure price_snapshot is valid
            price = float(item.get("price_snapshot", 0.0))
            item["price_snapshot"] = price

            # Recalculate subtotal
            item["subtotal"] = qty * price

        # Save serialized cart in Redis with TTL
        r.setex(redis_key, ttl, json.dumps(cart_data))
    except (TypeError, ValueError):
        # Corrupt cart_data → delete key
        r.delete(redis_key)


# -------------------- CLEAR CART --------------------
def clear_cart(key):
    """
    Remove the cart completely from Redis.
    """
    redis_key = f"cart:{key}"
    r.delete(redis_key)


# -------------------- UPDATE CART ITEM --------------------
def update_cart_item(key, product_id, quantity=None, price=None):
    """
    Update an existing item in Redis cart.
    If quantity is None, do not change it.
    If price is None, do not change it.
    Recalculates subtotal automatically.
    Returns True if item exists and updated, False otherwise.
    """
    cart = get_cart(key)
    pid = str(product_id)

    if pid not in cart:
        return False  # item does not exist

    # Update quantity if provided
    if quantity is not None:
        cart[pid]["quantity"] = max(int(quantity), 0)

    # Update price if provided
    if price is not None:
        cart[pid]["price_snapshot"] = float(price)

    # Recalculate subtotal
    cart[pid]["subtotal"] = cart[pid]["quantity"] * cart[pid]["price_snapshot"]

    save_cart(key, cart)
    return True


# -------------------- ADD/INCREMENT CART ITEM --------------------
def add_or_increment_cart_item(key, product_id, quantity=1, price=0.0):
    """
    Adds a new item to cart or increments the quantity if it exists.
    Automatically calculates subtotal.
    """
    cart = get_cart(key)
    pid = str(product_id)

    if pid in cart:
        cart[pid]["quantity"] += int(quantity)
    else:
        cart[pid] = {
            "quantity": int(quantity),
            "price_snapshot": float(price),
            "subtotal": int(quantity) * float(price)
        }

    # Always recalc subtotal to ensure correctness
    cart[pid]["subtotal"] = cart[pid]["quantity"] * cart[pid]["price_snapshot"]
    save_cart(key, cart)
    return cart[pid]


 



