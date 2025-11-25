from django.conf import settings
from paystackapi.paystack import Paystack

paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)


def initialize_transaction(email, amount, reference):
    """
    Initialize a Paystack transaction.
    Returns the response from Paystack.
    """
    response = paystack.transaction.initialize(
        amount=int(amount * 100), email=email, reference=reference  # Convert to kobo
    )
    return response


def verify_transaction(reference):
    """
    Verify a Paystack transaction using its reference.
    Returns the response from Paystack.
    """
    response = paystack.transaction.verify(reference)
    return response
