import asyncio
import telegram
import os
import datetime

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, reverse
import stripe
from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.urls import reverse

from book.models import Book
from borrowing.models import Borrowing, Payment
from borrowing.serializers import (
    BorrowingListSerializer,
    BorrowingDetailSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
    PaymentListSerializer,
    PaymentDetailSerializer,
)


BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=BOT_TOKEN)
stripe.api_key = os.environ.get("STRIPE_KEY")


class BorrowingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)
    queryset = Borrowing.objects.select_related("book", "user")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BorrowingDetailSerializer
        if self.action == "create":
            return BorrowingCreateSerializer
        if self.action == "return_book":
            return BorrowingReturnSerializer
        return BorrowingListSerializer

    def get_queryset(self) -> QuerySet:
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        borrowing = Borrowing.objects.all()

        data = request.data.copy()
        data["user"] = request.user.id
        book = Book.objects.get(id=request.data.get("book"))
        if book.inventory <= 0:
            raise Exception("No book available")

        if borrowing.filter(book=book, user=request.user):
            raise Exception("You borrowed this book")

        if borrowing.filter(payments__status__in=("PENDING",), user=request.user):
            raise Exception(
                "You are not allowed to borrow " "new books due to pending payments."
            )

        book.inventory -= 1
        book.save()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        async def send_message(text):
            await bot.send_message(
                chat_id=CHAT_ID,
                text=f"Borrowing created with ID {serializer.data['id']}",
            )

        asyncio.run(send_message(serializer.data))

        borrowing_id = serializer.data["id"]
        url = reverse("borrowing:create-checkout-session", args=[borrowing_id])

        return HttpResponseRedirect(url)

    @action(
        methods=["POST"],
        detail=True,
        url_path="return",
    )
    def return_book(self, request, pk):
        borrowing = self.get_object()
        book = Book.objects.get(borrowings=pk)
        with transaction.atomic():
            if borrowing.actual_return_date is None:
                book.inventory += 1
                book.save()
                borrowing.actual_return_date = datetime.date.today()
                borrowing.save()
                serializer = self.get_serializer(data=request.data)
                if serializer.is_valid(raise_exception=True):
                    if borrowing.fine_days:
                        url = reverse(
                            "borrowing:create-checkout-session",
                            args=[borrowing.id],
                        )
                        return HttpResponseRedirect(url)

                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(status=status.HTTP_403_FORBIDDEN)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "is_active",
                type=OpenApiTypes.BOOL,
                description="Filter by is active now( True or False)",
            ),
            OpenApiParameter(
                "user_id",
                type=OpenApiTypes.INT,
                description="Filter by user id for admin user only",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        is_active = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user_id")
        if is_active:
            if is_active.lower() == "true":
                queryset = queryset.filter(actual_return_date=None)
            else:
                queryset = queryset.exclude(actual_return_date=None)
        if request.user.is_staff and user_id:
            queryset = queryset.filter(user=user_id)

        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)
    queryset = Payment.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PaymentDetailSerializer
        if self.action in ("payment_success", "cancel_payment"):
            return PaymentDetailSerializer
        return PaymentListSerializer

    def get_queryset(self):
        queryset = Payment.objects.all()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(borrowing__user=self.request.user)

    @action(
        methods=["GET"],
        detail=True,
        url_path="success",
    )
    def payment_success(self, request, pk):
        session_id = self.get_object().session_id

        with transaction.atomic():
            checkout_session = stripe.checkout.Session.retrieve(session_id)

            payment_id = checkout_session.metadata["payment_id"]
            payment = Payment.objects.get(id=payment_id)

            payment.session_id = checkout_session.id
            payment.money_to_pay = checkout_session.amount_total / 100
            payment.status = "PAID"
            payment.type_session = "PAYMENT"
            payment.money_to_pay = 0
            payment.save()

            borrowing = payment.borrowing
            borrowing.save()

            serializer = self.get_serializer(payment, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                async def send_message(text):
                    await bot.send_message(chat_id=CHAT_ID, text=text)

                asyncio.run(send_message(serializer.data))

                return Response(serializer.data)
            return Response(serializer.errors)

    @action(
        methods=["GET"],
        detail=True,
        url_path="cancel",
    )
    def cancel_payment(self, request, pk):
        payment = get_object_or_404(Payment, id=pk)

        if payment.status == "PAID":
            return Response(status=status.HTTP_403_FORBIDDEN)

        payment.status = Payment.STATUS_CHOICES[0][0]
        payment.type_session = Payment.TYPE_CHOICES[0][0]
        payment.save()

        serializer = self.get_serializer(payment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)


class CreateCheckoutSessionView(APIView):
    @transaction.atomic
    def post(self, request, borrowing_id):
        if not request.user:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        borrowing = Borrowing.objects.get(id=borrowing_id)

        if Payment.objects.filter(borrowing_id=borrowing_id).exists():
            payment = Payment.objects.get(borrowing_id=borrowing_id)
            if payment.status == "PENDING" and borrowing.fine_days:
                payment.money_to_pay += borrowing.total_fine_amount

            if payment.status == "PAID" and borrowing.fine_days:
                payment.money_to_pay = borrowing.total_fine_amount
                payment.type_session = payment.TYPE_CHOICES[1][0]

            if payment.status == "PAID" and not borrowing.fine_days:
                return Response(status=status.HTTP_303_SEE_OTHER)
        else:
            payment = Payment.objects.create(
                borrowing=borrowing,
                money_to_pay=borrowing.total_fine_amount,
                type_session="PAYMENT",
            )

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": borrowing.book.title,
                        },
                        "unit_amount": int(payment.money_to_pay * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=request.build_absolute_uri(
                reverse("borrowing:payment-success", args=[payment.id])
            ),
            cancel_url=request.build_absolute_uri(
                reverse("borrowing:cancel-payment", args=[payment.id])
            ),
            metadata={"payment_id": payment.id},
        )

        payment.session_id = session.id
        payment.session_url = session.url
        payment.save()

        return HttpResponseRedirect(session.url)
