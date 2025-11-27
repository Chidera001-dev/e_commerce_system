import os
import services.shipping_service as shipping_service
from decimal import Decimal
from django.conf import settings
from orders.models import Order


# Initialize Shippo API key
SHIPPO_API_KEY = os.getenv("SHIPPO_API_KEY", settings.SHIPPO_API_KEY)
shipping_service.api_key = SHIPPO_API_KEY


def calculate_shipping_fee(cart_items=None, shipping_address=None):
    """
    Simple shipping fee calculator.
    """
    base_fee = Decimal("500.00")  # Base shipping fee in Naira
    per_item_fee = Decimal("100.00")  # Fee per product
    item_count = sum(item.quantity for item in cart_items) if cart_items else 1
    return base_fee + per_item_fee * item_count


def create_shipment(order: Order):
    """
    Creates a shipment in Shippo for a given order.
    Returns dict with tracking_number, label_url, status, provider, shipping_cost.
    """

    # Extract customer address
    to_address = {
        "name": order.shipping_full_name,
        "street1": order.shipping_address,
        "city": order.shipping_city,
        "state": order.shipping_state,
        "zip": order.shipping_postal_code,
        "country": order.shipping_country or "NG",
        "phone": order.shipping_phone,
        "email": order.user.email if order.user else "customer@example.com",
    }

    # Store address
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

    # Parcel info
    parcel = {
        "length": "10",
        "width": "10",
        "height": "10",
        "distance_unit": "cm",
        "weight": "1",
        "mass_unit": "kg",
    }

    try:
        # Create shipment
        shipment = shipping_service.Shipment.create(
            address_from=from_address,
            address_to=to_address,
            parcels=[parcel]
        )

        #  Extract shipping rates
        rates = shipment.get("rates", [])
        if not rates:
            raise Exception("No shipping rates returned by Shippo")

        # Pick first rate for demo
        selected_rate = rates[0]

        #  Purchase shipping label (transaction)
        transaction = shipping_service.Transaction.create(
            rate=selected_rate["object_id"],
            label_file_type="PDF"
        )

        if transaction["status"] != "SUCCESS":
            raise Exception(f"Transaction failed: {transaction.get('messages')}")

        #  Return useful info
        return {
            "tracking_number": transaction.get("tracking_number"),
            "label_url": transaction.get("label_url"),
            "status": "ready_for_pickup",
            "provider": "Shippo",
            "shipping_cost": Decimal(selected_rate.get("amount_local", selected_rate.get("amount")))  # NGN safe
        }

    except Exception as e:
        raise Exception(f"Failed to create shipment with Shippo: {e}")


def create_shipment_label(shipment):
    """
    Create a label for an existing shipment record.
    """

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

    to_address = {
        "name": shipment.order.shipping_full_name,
        "street1": shipment.order.shipping_address,
        "city": shipment.order.shipping_city,
        "state": shipment.order.shipping_state,
        "zip": shipment.order.shipping_postal_code,
        "country": shipment.order.shipping_country or "NG",
        "phone": shipment.order.shipping_phone,
        "email": shipment.order.user.email,
    }

    parcel = {
        "length": "10",
        "width": "10",
        "height": "10",
        "distance_unit": "cm",
        "weight": "1",
        "mass_unit": "kg",
    }

    try:
        # Create new shipment for this label
        shipment_obj = shipping_service.Shipment.create(
            address_from=from_address,
            address_to=to_address,
            parcels=[parcel]
        )

        rates = shipment_obj.get("rates", [])
        if not rates:
            raise Exception("No shipping rates returned by Shippo.")

        # Pick cheapest
        selected_rate = rates[0]

        #  Buy label
        transaction = shipping_service.Transaction.create(
            rate=selected_rate["object_id"],
            label_file_type="PDF"
        )

        if transaction["status"] != "SUCCESS":
            raise Exception(f"Shippo label error: {transaction.get('messages')}")

        return (
            transaction.get("label_url"),
            transaction.get("tracking_number"),
            transaction.get("eta"),  # estimated delivery date
        )

    except Exception as e:
        raise Exception(f"Failed to create shipment label via Shippo: {e}")
