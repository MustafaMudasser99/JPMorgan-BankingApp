import uuid
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

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

    SAVINGS_INTEREST_RATE = Decimal('0.020')
    # Savers Plus is 1 percentage point higher than Savings.
    SAVERS_PLUS_INTEREST_RATE = Decimal('0.030')

    def __str__(self):
        return self.name

    def get_balance(self):
        """
        Calculate the current balance from starting balance + transactions.
        """
        outgoing = Transaction.objects.filter(from_account=self).aggregate(models.Sum('amount'))['amount__sum'] or 0
        incoming = Transaction.objects.filter(to_account=self).aggregate(models.Sum('amount'))['amount__sum'] or 0
        return self.starting_balance + incoming + outgoing

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
        """
        Calculate the current balance by adding all transactions to the starting balance.
        """
        # Get all outgoing transactions (negative amounts)
        outgoing = Transaction.objects.filter(from_account=self).aggregate(models.Sum('amount'))['amount__sum'] or 0
        
        # Get all incoming transactions (positive amounts)
        incoming = Transaction.objects.filter(to_account=self).aggregate(models.Sum('amount'))['amount__sum'] or 0
        
        # Return the balance
        return self.starting_balance + incoming + outgoing

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

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    from_account = models.ForeignKey(Account, related_name='outgoing_transactions', on_delete=models.CASCADE)
    to_account = models.ForeignKey(Account, related_name='incoming_transactions', on_delete=models.CASCADE, null=True, blank=True)
    business = models.ForeignKey(Business, related_name='transactions', on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"

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