from django.db import models


class Book(models.Model):
    COVER_CHOICES = [("HARD", "hard"), ("SOFT", "soft")]

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(
        max_length=4,
        choices=COVER_CHOICES,
    )
    inventory = models.IntegerField()
    daily_fee = models.DecimalField(max_digits=None, decimal_places=2)
