import uuid
import math
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

class UserProfile(models.Model):
    """
    Stores persistent per-user preferences for the web experience.
    """
    DASHBOARD_WIDGET_CHOICES = [
        ('overview', 'Account overview'),
        ('transactions', 'Transactions'),
        ('accounts', 'Accounts'),
        ('quick_transfer', 'Quick Transfer menu'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    oobe_completed = models.BooleanField(default=False)
    selected_account_types = models.JSONField(default=list, blank=True)  # e.g. ["current","savings","saversplus"]
    dashboard_widgets = models.JSONField(default=list, blank=True)       # e.g. ["overview","transactions","accounts"]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"UserProfile({self.user.username})"


class Account(models.Model):
    ACCOUNT_TYPES = [
        ('current', 'Current'),
        ('savings', 'Savings'),
        ('savingsplus', 'Savings Plus'),
        ('saversplus', 'Savers Plus'),
        ('credit', 'Credit'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    starting_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    round_up_enabled = models.BooleanField(default=False)
    postcode = models.CharField(max_length=10, null=True, blank=True)
    round_up_pot = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # Add user field to associate with Django User
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts', null=True, blank=True)
    # Add account type field
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='current')
    night_time_savings_enabled = models.BooleanField(default=False)

    SAVINGS_INTEREST_RATE = Decimal('0.020')
    # Savers Plus is 1 percentage point higher than Savings.
    SAVERS_PLUS_INTEREST_RATE = Decimal('0.030')

    def __str__(self):
        return self.name

    def get_balance(self):
        outgoing = Transaction.objects.filter(from_account=self, status='completed').aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        incoming = Transaction.objects.filter(to_account=self, status='completed').aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        return self.starting_balance + incoming - outgoing

    def get_interest_rate(self):
        """
        Returns the nominal interest rate (as a decimal, e.g. 0.02 == 2%).
        """
        if self.account_type == 'saversplus':
            return self.SAVERS_PLUS_INTEREST_RATE
        if self.account_type in ('savings', 'savingsplus'):
            return self.SAVINGS_INTEREST_RATE
        return Decimal('0.000')
    
class Card(models.Model):
    """
    Represents a bank card linked to a specific Account.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='cards')
    card_holder_name = models.CharField(max_length=255)
    card_number = models.CharField(max_length=16, unique=True)
    expiry_date = models.CharField(max_length=5) # Format: MM/YY
    cvv = models.CharField(max_length=3)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Card ****{self.card_number[-4:]} for {self.account.name}"
        
    def get_balance(self):
        outgoing = Transaction.objects.filter(from_account=self, status='completed').aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        incoming = Transaction.objects.filter(to_account=self, status='completed').aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        return self.starting_balance + incoming - outgoing
class Business(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    sanctioned = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('withdrawal', 'Withdrawal'),
        ('deposit', 'Deposit'),
        ('collect_roundup', 'Collect Roundup'),
        ('transfer', 'Transfer'),
        ('roundup_reclaim', 'Round Up Reclaim'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('completed', 'Completed'),
        ('denied', 'Denied'),
        ('expired', 'Timed Out'),
    ]

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    from_account = models.ForeignKey(Account, related_name='outgoing_transactions', on_delete=models.CASCADE)
    to_account = models.ForeignKey(Account, related_name='incoming_transactions', on_delete=models.CASCADE, null=True, blank=True)
    business = models.ForeignKey(Business, related_name='transactions', on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField( max_length=20, choices=STATUS_CHOICES, default='completed')
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"
    
    def is_expired(self):
        if self.status == 'pending' and self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)
        if is_new and self.transaction_type == 'payment' and self.from_account.round_up_enabled:
            savings_account = self.from_account.user.accounts.filter(account_type='savings').first()
            if savings_account:
                amount_val = abs(Decimal(str(self.amount)))
                ceiling_val = Decimal(math.ceil(amount_val))
                round_up_amount = ceiling_val - amount_val

                if round_up_amount > 0:
                    Transaction.objects.create(
                        transaction_type='collect_roundup',
                        amount=round_up_amount,
                        from_account=self.from_account,
                        to_account=savings_account
                    )

class SavingsTracker(models.Model):
    # 1. Link directly to the Account, restricted to 'savings' type
    account = models.OneToOneField(
        'Account', 
        on_delete=models.CASCADE, 
        related_name='savings_tracker',
        limit_choices_to={'account_type': 'savings'} 
    )
    
    savings_enabled = models.BooleanField(default=False)
    savings_goal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # current_amount Field REMOVED. Replaced with the @property below.
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Savings Tracker for {self.account.name}: {self.current_amount}/{self.savings_goal}"

    @property
    def current_amount(self):
        incoming = self.account.incoming_transactions.aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        outgoing = self.account.outgoing_transactions.aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        balance = self.account.starting_balance + incoming - outgoing
        return balance

    def progress_percentage(self):
        """Calculate how close the user is to their goal."""
        if self.savings_goal <= 0:
            return 0
        return (self.current_amount / self.savings_goal) * 100

class ChatMessage(models.Model):
    """
    Stores the conversation history for the AI Assistant.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_history")
    text = models.TextField()
    # 'user' for human messages, 'assistant' for bot replies
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.text[:20]}"    
