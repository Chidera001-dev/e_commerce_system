from django.conf import settings
from paystackapi.paystack import Paystack

paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)


def initialize_transaction(email, amount, reference, currency="NGN"):
    """
    Initialize Paystack transaction.
    - NGN is sent in kobo (amount * 100)
    - USD is sent as-is (NO multiplication)
    """

    if currency.upper() == "NGN":
        paystack_amount = int(amount * 100)  # convert to kobo
    else:
        paystack_amount = float(amount)  # USD, GHS, ZAR → NO conversion

    response = paystack.transaction.initialize(
        email=email,
        amount=paystack_amount,
        reference=reference,
        currency=currency.upper(),
    )
    return response


def verify_transaction(reference):
    """
    Verify Paystack transaction by its reference.
    """
    return paystack.transaction.verify(reference)
