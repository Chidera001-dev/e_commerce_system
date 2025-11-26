from django.conf import settings
from paystackapi.paystack import Paystack

paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)


def initialize_transaction(email, amount, reference):
    """
    Initialize a Paystack transaction.
    `amount` must be in Naira (decimal).
    Converts to kobo internally.
    """
    response = paystack.transaction.initialize(
        amount=int(amount * 100),  # convert Naira to kobo
        email=email,
        reference=reference,
    )
    return response


def verify_transaction(reference):
    """
    Verify a Paystack transaction by its reference.
    """
    response = paystack.transaction.verify(reference)
    return response({"message": "Payment processed successfully"}, status=200)
