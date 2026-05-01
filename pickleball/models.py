from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

# COURT MODEL
class Adminn(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.username


class courts(models.Model):
    name = models.CharField(max_length=100)
    game_type = models.CharField(max_length=50)
    location = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='courts/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.game_type}"
   # make sure this import matches your court model

class Booking(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    # optional link to registered User
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # customer details
    name = models.CharField(max_length=80)
    email = models.EmailField()

    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^[6-9]\d{9}$', 'Enter a valid 10-digit phone number starting with 6–9')],
        blank=True
    )

    address = models.TextField(blank=True)

    # court details
    court = models.ForeignKey(courts, on_delete=models.PROTECT)
    date = models.DateField()               # correct date field
    time_slot = models.CharField(max_length=32)

    # payment fields
    payment_method = models.CharField(
        max_length=8,
        choices=PAYMENT_CHOICES,
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=8,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.court.name} - {self.date} [{self.time_slot}]"

    class Meta:
        # Prevent duplicate bookings for same court/date/slot
        unique_together = ('court', 'date', 'time_slot')
        indexes = [
            models.Index(fields=['court', 'date', 'time_slot']),
        ]

    def __str__(self):
        return f"{self.name} - {self.court} @ {self.time_slot} - {self.date} [{self.status}]"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^[6-9]\d{9}$', 'Enter a valid 10-digit phone number starting with 6-9')],
        unique=True
    )

    def __str__(self):
        return self.user.username
