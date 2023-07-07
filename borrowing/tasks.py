from datetime import date, timedelta


from borrowings.models import Borrowing
from borrowings.notification_service import send_telegram_message


def check_overdue_borrowings_task():
    today = date.today()
    tomorrow = today + timedelta(days=1)

    overdue_borrowings = Borrowing.objects.filter(
        expected_return_date__lte=tomorrow, actual_return_date=None
    )

    if overdue_borrowings.exists():
        for borrowing in overdue_borrowings:
            message = (
                f"Overdue borrowing:\n"
                f"Borrowing ID: {borrowing.id}\n"
                f"User: {borrowing.user.email}\n"
                f"Book: {borrowing.book.title}"
            )
            send_telegram_message(message)
    else:
        message = "No borrowings overdue today!"
        send_telegram_message(message)
