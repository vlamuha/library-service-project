from django.utils import timezone
import datetime
import telegram
from dotenv import load_dotenv
from celery.schedules import crontab
import asyncio
import os

from borrowing.models import Borrowing
from borrowing.serializers import BorrowingDetailSerializer
from library_service.celery import app


load_dotenv()
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=BOT_TOKEN)


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour=19, minute=25),
        fun=check_and_send_to_telegram.s(),
    )


@app.task
def check_and_send_to_telegram():
    tomorrow = timezone.now() + datetime.timedelta(days=1)
    borrowings = Borrowing.objects.filter(expected_return_date__lte=tomorrow).all()

    async def send_message(text):
        await bot.send_message(chat_id=CHAT_ID, text=text)

    message_telegram = []
    if borrowings:
        for borrowing in borrowings:
            borrowing_dict = BorrowingDetailSerializer(borrowing).data
            message_telegram.append(
                f"User {borrowing_dict['user']} "
                f"return to - {borrowing_dict['expected_return_date']}."
            )
    else:
        message_telegram = "No borrowings overdue today!"
    asyncio.run(send_message(message_telegram))
