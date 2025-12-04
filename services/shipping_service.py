import string
import random
import requests
from decimal import Decimal
from shippo import Shippo
from shippo.models import components
from django.conf import settings
import os

shippo_client = Shippo(api_key_header=settings.SHIPPO_API_KEY)

def generate_random_tracking(length=12):
    """Generate a random alphanumeric tracking number."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def calculate_shipping_fee(cart_items=None, shipping_address=None):
    base_fee = Decimal("200.00")
    per_item_fee = Decimal("100.00")
    item_count = sum(item.quantity for item in cart_items) if cart_items else 1
    return base_fee + per_item_fee * item_count

def create_shipment_label(order, shipment, download_path="labels"):
    try:
        shipment_request = components.ShipmentCreateRequest(
            address_from=components.Address(
                name="Chidera Solutions LLC",
                street1="525 Brannan St",
                city="San Francisco",
                state="CA",
                zip="94107",
                country="US",
                email="sender@example.com",
                phone="+14155551234"
            ),
            address_to=components.Address(
                name=order.shipping_full_name,
                street1=order.shipping_address_text,
                city=order.shipping_city,
                state=order.shipping_state or "CA",
                zip=order.shipping_postal_code or "94107",
                country="US",
                email=order.user.email if order.user else "customer@example.com",
                phone=order.shipping_phone or "+14155551234"
            ),
            parcels=[components.Parcel(
                length="10",
                width="10",
                height="10",
                distance_unit="cm",
                weight="1",
                mass_unit="kg"
            )],
            test=True
        )

        created_shipment = shippo_client.shipments.create(shipment_request)
        if not created_shipment.rates:
            raise Exception("No shipping rates returned by Shippo")

        selected_rate = created_shipment.rates[0]

        transaction_request = components.TransactionCreateRequest(
            rate=selected_rate.object_id,
            label_file_type="PDF",
            async_=False
        )

        transaction = shippo_client.transactions.create(transaction_request)
        if transaction.status != "SUCCESS":
            raise Exception(f"Transaction failed: {transaction.messages}")

        # Use Shippo tracking number if available; otherwise, generate a random one
        tracking_number = getattr(transaction, "tracking_number", None) or generate_random_tracking()

        # Download PDF for local testing
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        pdf_url = transaction.label_url
        pdf_response = requests.get(pdf_url)
        pdf_filename = os.path.join(download_path, f"{order.id}_label.pdf")
        with open(pdf_filename, "wb") as f:
            f.write(pdf_response.content)

        return {
            "label_url": pdf_filename,
            "tracking_number": tracking_number,
            "carrier": getattr(transaction, "tracking_provider", "UPS"),
            "status": "in_transit"
        }

    except Exception as e:
        raise Exception(f"Failed to create shipment label: {str(e)}")
