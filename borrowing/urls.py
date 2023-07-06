from django.urls import path
from rest_framework.routers import DefaultRouter
from borrowing.views import (
    BorrowingViewSet,
    PaymentViewSet,
    CreateCheckoutSessionView
)

router = DefaultRouter()
router.register(r'borrowings', BorrowingViewSet, basename='borrowings')
router.register(r'payments', PaymentViewSet, basename='payments')

urlpatterns = [
    path(
        'payments/create-checkout-session/<int:borrowing_id>/',
        CreateCheckoutSessionView,
        name='create-checkout-session'
    ),
] + router.urls

app_name = 'borrowing'
