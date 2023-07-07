from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from books.serializers import BookSerializer
from borrowings.models import Borrowing, Payment
from borrowings.notification_service import send_telegram_message
from borrowings.payment_service import create_stripe_session


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "status",
            "type",
            "borrowing",
            "session_url",
            "session_id",
            "money_to_pay",
        )


class BorrowingSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "payments",
        )
        read_only_fields = ("id", "borrow_date", "actual_return_date", "user")

    def validate(self, attrs):
        user = self.context["request"].user

        if Payment.objects.filter(
            borrowing__user=user, status=Payment.StatusChoices.PENDING
        ).exists():
            raise serializers.ValidationError(
                "You have pending payments. Cannot borrow a new book."
            )

        return attrs

    def validate_book(self, book):
        if book.inventory == 0:
            raise serializers.ValidationError(
                "Book is not available for borrowing."
            )
        return book

    @transaction.atomic
    def create(self, validated_data):
        book = validated_data["book"]
        user = self.context["request"].user

        borrowing = Borrowing.objects.create(
            expected_return_date=validated_data["expected_return_date"],
            book=book,
            user=user,
        )

        create_stripe_session(self.context["request"], borrowing)

        book.inventory -= 1
        book.save()

        message = (
            f"New borrowing created:\nUser: {user.email}\nBook: {book.title}"
        )
        send_telegram_message(message)

        return borrowing


class BorrowingListSerializer(BorrowingSerializer):
    book = BookSerializer(read_only=True)
    user = serializers.ReadOnlyField(source="user.email")


class BorrowingReturnSerializer(BorrowingSerializer):
    expected_return_date = serializers.ReadOnlyField()
    book = serializers.ReadOnlyField()

    def validate(self, attrs):
        borrowing = self.instance

        if borrowing.actual_return_date is not None:
            raise serializers.ValidationError("Book has already been returned")

        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        borrowing = self.instance
        borrowing.actual_return_date = timezone.now().date()
        borrowing.save()

        book = borrowing.book
        book.inventory += 1
        book.save()

        if borrowing.actual_return_date > borrowing.expected_return_date:
            fine_amount = borrowing.fine_price

            Payment.objects.create(
                status=Payment.StatusChoices.PENDING,
                type=Payment.TypeChoices.FINE,
                borrowing=borrowing,
                money_to_pay=fine_amount,
            )

        return borrowing
