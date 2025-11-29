import os
from decimal import Decimal
from django.conf import settings
import services.shipping_service as shipping_service
from orders.models import Order
from .models import Shipment, ShippingAddress

# Shippo API key
SHIPPO_API_KEY = os.getenv("SHIPPO_API_KEY", settings.SHIPPO_API_KEY)
shipping_service.api_key = SHIPPO_API_KEY

def calculate_shipping_fee(cart_items=None, shipping_address=None):
    """Simple shipping fee calculator based on items count."""
    base_fee = Decimal("500.00")
    per_item_fee = Decimal("100.00")
    item_count = sum(item.quantity for item in cart_items) if cart_items else 1
    return base_fee + per_item_fee * item_count

def create_shipment(shipment: Shipment):
    """Create shipment in Shippo using Shipment and ShippingAddress info."""
    address_obj = shipment.order.shipping_addresses  

    to_address = {
        "name": address_obj.full_name,
        "street1": address_obj.address_line1,
        "street2": address_obj.address_line2 or "",
        "city": address_obj.city,
        "state": address_obj.state,
        "zip": address_obj.postal_code or "",
        "country": address_obj.country or "NG",
        "phone": address_obj.phone_number,
        "email": shipment.order.user.email if shipment.order.user else "customer@example.com",
    }

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

    parcel = {
        "length": "10",
        "width": "10",
        "height": "10",
        "distance_unit": "cm",
        "weight": "1",
        "mass_unit": "kg",
    }

    try:
        shipment_obj = shipping_service.Shipment.create(
            address_from=from_address, address_to=to_address, parcels=[parcel]
        )

        rates = shipment_obj.get("rates", [])
        if not rates:
            raise Exception("No shipping rates returned by Shippo")

        selected_rate = rates[0]

        transaction = shipping_service.Transaction.create(
            rate=selected_rate["object_id"], label_file_type="PDF"
        )

        if transaction["status"] != "SUCCESS":
            raise Exception(f"Shippo transaction failed: {transaction.get('messages')}")

        # Update shipment object
        shipment.tracking_number = transaction.get("tracking_number")
        shipment.delivery_status = "ready_for_pickup"
        shipment.courier_name = "Shippo"
        shipment.shipping_fee = Decimal(selected_rate.get("amount_local", selected_rate.get("amount")))
        shipment.save()

        return {
            "tracking_number": shipment.tracking_number,
            "label_url": transaction.get("label_url"),
            "delivery_status": shipment.delivery_status,
            "courier_name": shipment.courier_name,
            "shipping_fee": shipment.shipping_fee,
        }

    except Exception as e:
        raise Exception(f"Failed to create shipment: {e}")

def create_shipment_label(shipment: Shipment):
    """Create or refresh shipment label for existing shipment."""
    result = create_shipment(shipment)
    return result["label_url"], result["tracking_number"], result.get("estimated_delivery_date")
