from rest_framework import serializers

from borrowing.models import Borrowing, Payment


class PaymentListSerializer(serializers.ModelSerializer):
    money_to_pay = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "status",
            "type_session",
            "session_url",
            "session_id",
            "money_to_pay",
            "borrowing",
        )

    def get_money_to_pay(self, obj):
        return obj.money_to_pay


class BorrowingListSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_author = serializers.CharField(source="book.author", read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book_title",
            "book_author",
            "user",
        )


class BorrowingDetailSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title")
    book_author = serializers.CharField(source="book.author")
    book_cover = serializers.CharField(source="book.cover")
    book_daily_fee = serializers.CharField(source="book.daily_fee")
    payments = PaymentListSerializer(many=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book_title",
            "book_author",
            "book_cover",
            "book_daily_fee",
            "payments",
            "user",
        )

        read_only_fields = (
            "book_title",
            "book_author",
            "book_cover",
            "book_daily_fee",
            "payments",
            "user",
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id", "book", "expected_return_date", "user")
        read_only_fields = ("user",)

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)


class BorrowingReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id",)


class PaymentDetailSerializer(serializers.ModelSerializer):
    borrowing = BorrowingListSerializer()

    class Meta:
        model = Payment
        fields = (
            "status",
            "type_session",
            "session_url",
            "session_id",
            "money_to_pay",
            "borrowing",
        )
