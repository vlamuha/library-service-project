from user.models import User
from django.db import models

from book.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(default=None, null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="borrowings")

    @property
    def total_fine_amount(self):
        if self.actual_return_date:
            days_late = (self.actual_return_date - self.expected_return_date).days
            if days_late > 0:
                return (self.book.daily_fee * days_late) * 2
        days_late = (self.expected_return_date - self.borrow_date).days
        if days_late > 0:
            return self.book.daily_fee * days_late
        return self.book.daily_fee * 1

    @property
    def fine_days(self):
        if self.actual_return_date is not None:
            return (self.actual_return_date - self.expected_return_date).days
        return False


class Payment(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "PENDING"),
        ("PAID", "PAID"),
    )

    TYPE_CHOICES = (
        ("PAYMENT", "PAYMENT"),
        ("FINE", "FINE"),
    )

    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0]
    )
    type_session = models.CharField(
        max_length=24, choices=TYPE_CHOICES, default=TYPE_CHOICES[0][0]
    )
    borrowing = models.ForeignKey(
        Borrowing, on_delete=models.CASCADE, related_name="payments"
    )
    session_url = models.URLField(null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    money_to_pay = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self) -> str:
        return (
            f"{self.get_status_display()}, "
            f"{self.get_type_session_display()} - "
            f"{self.borrowing}"
        )
