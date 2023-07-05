# library-service-project

# FEATURES
Added borrowing model with constraints for borrow_date, expected_return_date, and actual_return_date.

Implemented a read serializer with detailed book info.

Implemented list & detail endpoints for borrowings.

Implemented Create Borrowing endpoint and create a serializer, validated book inventory is not 0, decreased inventory by 1 for book, attached the current user to the borrowing, added filtering for the Borrowings List endpoint, ensured that all non-admins can see only their borrowings, ensured that borrowings are available only for authenticated users, added the is_active parameter for filtering by active borrowings (still not returned), added the user_id parameter for admin users so admin can see all users’ borrowings, if not specified, but if specified - only for a concrete user.

Implemented return Borrowing functionality, ensured that you cannot return borrowing twice, added 1 to book inventory on returning, added an endpoint for it.

Implemented the possibility of sending notifications on each Borrowing creation, set up a telegram chat for notifications posting in there, set up a telegram bot for sending notifications, investigated the sendMessage function interface in Telegram API, ensured that all private data is private and never enters the GitHub repo, created a helper for sending messages to the notifications chat through Telegram API, integrated sending notifications on new borrowing creation (provided info about this borrowing in the message).

Implemented a daily-based function for checking borrowings overdue, ensured that the function filters all borrowings, which are overdue (expected_return_date is tomorrow or less, and the book is still not returned) and send a notification to the telegram chat about each overdue separately with detailed information.

Automated the routine of creating Stripe Payment Sessions, created a Payment model, created serializer & views for list and detail endpoints for payments, ensured non-admins can see only their payments when admins can see all of them, created a Stripe Payment Session, taking a deep dive into the stripe doc to understand how to work with payments, manually created 1-2 Payments in the Library system, and attach existing session_url and session_id to each, checked List & Detail endpoint are working.

Created a helper function, which receives borrowing as a parameter, and creates a new Stripe Session for it, calculated the total price of borrowing and set it as the unit amount. Let quantity as 1 - we allow borrowing only 1 book at a time, created a Payment and stored session_url and session_id inside. Attached Borrowing to the Payment, added payments to Borrowing serializers, so all payments associated with current Borrowing will be displayed.

Implemented success and cancel URLs for Payment Service, created success action in which you checked that stripe session was paid, and if it was successful, marked payment as paid, created a Cancel endpoint, which says to the user that the payment was canceled.


# How to run
Python3 must be already installed

```shell
git clone https://github.com/vlamuha/library-service-project
cd library_service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```
