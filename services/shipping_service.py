import os
from decimal import Decimal
from django.conf import settings
import shippo

# -------------------------------
# Shippo API Key
# -------------------------------
SHIPPO_API_KEY = os.getenv("SHIPPO_API_KEY", getattr(settings, "SHIPPO_API_KEY", ""))
shippo.api_key = SHIPPO_API_KEY

# -------------------------------
# Shipping Fee Calculator
# -------------------------------
def calculate_shipping_fee(cart_items=None, shipping_address=None):
    """
    Simple shipping fee calculation based on the number of items in cart.
    """
    base_fee = Decimal("500.00")
    per_item_fee = Decimal("100.00")
    item_count = sum(item.quantity for item in cart_items) if cart_items else 1
    return base_fee + per_item_fee * item_count

# -------------------------------
# Create Shipment & Label
# -------------------------------
def create_shipment(shipment):
    """
    Creates a shipment using Shippo 3.x API, purchases a label,
    saves tracking info to your Shipment model, and returns shipment data.
    """
    order = shipment.order

    # TO Address — Customer
    to_address = {
        "name": order.shipping_full_name,
        "street1": order.shipping_address_text,
        "city": order.shipping_city,
        "state": order.shipping_state,
        "zip": order.shipping_postal_code or "",
        "country": order.shipping_country or "NG",
        "phone": order.shipping_phone,
        "email": order.user.email if order.user else "customer@example.com",
    }

    # FROM Address — Store
    from_address = {
        "name": "Twizzy Store",
        "street1": "no 17 Ayayiba street maryland Enugu",
        "city": "Enugu",
        "state": "Enugu",
        "zip": "100001",
        "country": "NG",
        "phone": "+2349060948412",
        "email": "no-reply@shop.com",
    }

    # Parcel
    parcel = {
        "length": "10",
        "width": "10",
        "height": "10",
        "distance_unit": "cm",
        "weight": "1",
        "mass_unit": "kg",
    }

    try:
        # -------------------------------
        # CREATE SHIPMENT
        # -------------------------------
        shipment_obj = shippo.Shipment.create_sync(
            address_from=from_address,
            address_to=to_address,
            parcels=[parcel]
        )

        rates = shipment_obj.get("rates", [])
        if not rates:
            raise Exception("Shippo did not return any shipping rates.")

        selected_rate = rates[0]  # pick the first available rate

        # -------------------------------
        # PURCHASE LABEL
        # -------------------------------
        transaction = shippo.Transaction.create_sync(
            rate=selected_rate["object_id"],
            label_file_type="PDF"
        )

        if transaction["status"] != "SUCCESS":
            raise Exception(f"Shippo transaction failed: {transaction.get('messages')}")

        # -------------------------------
        # SAVE TO SHIPMENT MODEL
        # -------------------------------
        shipment.shipping_tracking_number = transaction.get("tracking_number")
        shipment.shipping_provider = selected_rate.get("provider", "Shippo")
        shipment.shipping_fee = Decimal(selected_rate.get("amount_local", selected_rate["amount"]))
        shipment.shipping_label_url = transaction.get("label_url")
        shipment.shipping_status = "in_transit"
        shipment.save()

        return {
            "tracking_number": shipment.shipping_tracking_number,
            "label_url": shipment.shipping_label_url,
            "courier": shipment.shipping_provider,
        }

    except Exception as e:
        raise Exception(f"Failed to create shipment: {e}")

# -------------------------------
# Wrapper for backward compatibility
# -------------------------------
def create_shipment_label(shipment):
    """
    Wrapper to match older interface: returns (label_url, tracking_number, shipping_status)
    """
    result = create_shipment(shipment)
    return result["label_url"], result["tracking_number"], "in_transit"
