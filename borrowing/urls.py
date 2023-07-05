from django.urls import path
from borrowing.views import (
    BorrowingViewSet,
    PaymentViewSet,
    create_checkout_session,
)


urlpatterns = [
    path(
        "borrowings/",
        BorrowingViewSet.as_view({"get": "list", "post": "create"}),
        name="borrowings-list",
    ),
    path(
        "borrowings/<int:pk>/",
        BorrowingViewSet.as_view({"get": "retrieve"}),
        name="borrowings-detail",
    ),
    path(
        "borrowings/<int:pk>/return/",
        BorrowingViewSet.as_view({"post": "return_book"}),
        name="borrowings-return",
    ),
    path(
        "payments/",
        PaymentViewSet.as_view({"get": "list"}),
        name="payments-list",
    ),
    path(
        "payments/<int:pk>/",
        PaymentViewSet.as_view({"get": "retrieve"}),
        name="payments-detail",
    ),
    path(
        "payments/create-checkout-session/<int:borrowing_id>/",
        create_checkout_session,
        name="create-checkout-session",
    ),
    path(
        "payments/<int:pk>/success/",
        PaymentViewSet.as_view({"get": "payment_success"}),
        name="payment-success",
    ),
    path(
        "payments/<int:pk>/cancel/",
        PaymentViewSet.as_view({"get": "cancel_payment"}),
        name="cancel-payment",
    ),
]

app_name = "borrowing"
