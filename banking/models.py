import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('current', 'Current'),
        ('savings', 'Savings'),
        ('savingsplus', 'Savings Plus'),
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

    def __str__(self):
        return self.name

    def get_balance(self):
        """
        Calculate the current balance from starting balance + transactions.
        """
        outgoing = Transaction.objects.filter(from_account=self).aggregate(models.Sum('amount'))['amount__sum'] or 0
        incoming = Transaction.objects.filter(to_account=self).aggregate(models.Sum('amount'))['amount__sum'] or 0
        return self.starting_balance + incoming + outgoing
    
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
        """
        Dynamically calculates the current amount based on the linked savings account.
        """
        # Calculate incoming and outgoing transactions for the linked account
        incoming = self.account.incoming_transactions.aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        outgoing = self.account.outgoing_transactions.aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        # Assuming outgoing transactions are stored as positive numbers that need to be subtracted. 
        # (If your system stores them as negative numbers, change the minus to a plus).
        balance = self.account.starting_balance + incoming - outgoing
        return balance

    def progress_percentage(self):
        """Calculate how close the user is to their goal."""
        if self.savings_goal <= 0:
            return 0
        return (self.current_amount / self.savings_goal) * 100
