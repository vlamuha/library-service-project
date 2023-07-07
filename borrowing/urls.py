from django.urls import path, include
from rest_framework import routers

from borrowings.views import BorrowingViewSet, PaymentViewSet

router = routers.DefaultRouter()
router.register("borrowings", BorrowingViewSet, basename="borrowing")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path(
        "payments/<int:pk>/success/",
        PaymentViewSet.as_view({"get": "payment_success"}),
        name="payment_success",
    ),
    path(
        "payments/<int:pk>/cancel/",
        PaymentViewSet.as_view({"get": "payment_cancel"}),
        name="payment_cancel",
    ),
] + router.urls

app_name = "borrowings"
