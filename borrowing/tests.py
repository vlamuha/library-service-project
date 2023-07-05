import os

import telegram
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from dotenv import load_dotenv
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from book.models import Book
from borrowing.models import Borrowing, Payment

load_dotenv()
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=BOT_TOKEN)
BORROWING_BOOK = reverse("borrowing_service:borrowings-list")


def sample_book(**params):
    defaults = {
        "title": "Sample movie",
        "author": "Sample description",
        "cover": "SOFT",
        "inventory": 2,
        "daily_fee": 2,
    }
    defaults.update(params)

    return Book.objects.create(**defaults)


class BorrowingModelTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )

    def test_borrowing_list(self):
        res = self.client.get(BORROWING_BOOK)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_borrowing_creation_and_redirect_to_pay(self):
        book = sample_book()
        payload = {
            "user": self.user,
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=14),
        }

        self.client.force_authenticate(self.user)
        res = self.client.post(BORROWING_BOOK, payload)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)

        new_object = Borrowing.objects.last()
        self.assertEqual(new_object.user, self.user)
        self.assertEqual(new_object.book.id, book.id)
        self.assertEqual(
            new_object.expected_return_date,
            timezone.now().date() + timedelta(days=14),
        )

    @patch("borrowing.views.telegram.Bot.send_message")
    def test_create_borrowing_sends_telegram_message(self, mock_send_message):
        book = sample_book()

        payload = {
            "user": self.user.id,
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=14),
        }

        url = reverse("borrowing_service:borrowings-list")
        self.client.force_authenticate(user=self.user)
        self.client.post(url, data=payload)
        new_object = Borrowing.objects.last()

        mock_send_message.assert_called_once_with(
            chat_id=CHAT_ID, text=f"Borrowing created with ID {new_object.id}"
        )

    def test_book_inventory_decremented_on_borrowing(self):
        book = sample_book()
        payload = {
            "user": self.user.id,
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=14),
        }
        url = reverse("borrowing_service:borrowings-list")
        self.client.force_authenticate(user=self.user)
        self.client.post(url, data=payload)

        book = Book.objects.last()
        self.assertEqual(book.inventory, 1)

    def test_borrowing_user_cannot_borrow_same_book_twice(self):
        book = sample_book()

        payload = {
            "user": self.user.id,
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=14),
        }
        url = BORROWING_BOOK
        self.client.force_authenticate(user=self.user)
        res = self.client.post(url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)

        with self.assertRaises(Exception) as context:
            self.client.post(url, data=payload)
        self.assertEqual(str(context.exception), "You borrowed this book")

    def test_user_cannot_borrow_if_book_not_available(self):
        book = Book.objects.create(
            title="Sample movie",
            author="Sample description",
            cover="SOFT",
            inventory=0,
            daily_fee=2,
        )

        payload = {
            "user": self.user.id,
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=14),
        }
        url = BORROWING_BOOK
        self.client.force_authenticate(user=self.user)

        with self.assertRaises(Exception) as context:
            self.client.post(url, data=payload)
        self.assertEqual(str(context.exception), "No book available")

    def test_user_cannot_borrow_new_book_if_pending_payments(self):
        book1 = sample_book()
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=book1,
            expected_return_date=timezone.now().date() + timedelta(days=14),
        )
        Payment.objects.create(
            borrowing=borrowing,
            money_to_pay=1,
        )
        book2 = Book.objects.create(
            title="Sample",
            author="Sample",
            cover="SOFT",
            inventory=3,
            daily_fee=2,
        )

        payload = {
            "user": self.user.id,
            "book": book2.id,
            "expected_return_date": timezone.now().date() + timedelta(days=14),
        }
        url = reverse("borrowing_service:borrowings-list")
        self.client.force_authenticate(user=self.user)
        with self.assertRaises(Exception) as context:
            self.client.post(url, data=payload)
        self.assertEqual(
            str(context.exception),
            "You are not allowed to borrow new books due to pending payments.",
        )

    def test_user_can_borrow_new_book_if_no_pending_payments(self):
        book1 = sample_book()
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=book1,
            expected_return_date=timezone.now().date() + timedelta(days=14),
        )
        Payment.objects.create(
            status="PAID",
            borrowing=borrowing,
            money_to_pay=1,
        )

        book2 = Book.objects.create(
            title="Sample",
            author="Sample",
            cover="SOFT",
            inventory=3,
            daily_fee=2,
        )
        payload = {
            "user": self.user.id,
            "book": book2.id,
            "expected_return_date": timezone.now().date() + timedelta(days=14),
        }
        url = BORROWING_BOOK
        self.client.force_authenticate(user=self.user)
        res = self.client.post(url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)

    def test_book_inventory_incremented_on_return(self):
        book = sample_book()
        payload1 = {
            "user": self.user.id,
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=14),
        }
        url = BORROWING_BOOK
        self.client.force_authenticate(user=self.user)
        self.client.post(url, data=payload1)

        payload2 = {
            "user": self.user.id,
            "book": book.id,
        }
        borrowing = Borrowing.objects.last()
        url = reverse("borrowing_service:borrowings-return", args=[borrowing.id])
        self.client.force_authenticate(user=self.user)
        self.client.post(url, data=payload2)

        book = Book.objects.last()
        self.assertEqual(book.inventory, 2)


class PaymentTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.book = sample_book()
        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=timezone.now().date() + timedelta(days=14),
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        payload = {
            "borrowing": self.borrowing.id,
            "money_to_pay": 10,
            "type_session": "PAYMENT",
        }
        url = reverse(
            "borrowing_service:create-checkout-session",
            args=[self.borrowing.id],
        )
        self.client.post(url, data=payload)

    def test_payment_success(self):
        payment = Payment.objects.last()

        url = reverse("borrowing_service:payment-success", args=[payment.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "PAID")

    def test_cancel_payment(self):
        payment = Payment.objects.last()
        url = reverse("borrowing_service:cancel-payment", args=[payment.id])
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Payment.STATUS_CHOICES[0][0])
