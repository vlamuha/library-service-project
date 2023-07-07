import os

import stripe
from django.db import transaction
from rest_framework.reverse import reverse

from borrowings.models import Payment


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


@transaction.atomic
def create_stripe_session(request, borrowing):
    total_price = borrowing.total_price
    unit_amount = int(total_price * 100)

    payment = Payment.objects.create(
        borrowing=borrowing,
        status=Payment.StatusChoices.PENDING,
        type=Payment.TypeChoices.PAYMENT,
        money_to_pay=total_price,
    )

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": unit_amount,
                    "product_data": {
                        "name": borrowing.book.title,
                    },
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=request.build_absolute_uri(
            reverse("borrowings:payment_success", kwargs={"pk": payment.pk})
        ),
        cancel_url=request.build_absolute_uri(
            reverse("borrowings:payment_cancel", kwargs={"pk": payment.pk})
        ),
    )

    payment.session_url = session.url
    payment.session_id = session.id
    payment.save()
