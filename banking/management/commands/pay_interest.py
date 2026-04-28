from django.core.management.base import BaseCommand
from django.db import transaction
from banking.models import Account, Transaction
from decimal import Decimal, ROUND_DOWN

class Command(BaseCommand):
    help = 'Calculates and applies monthly interest to eligible savings accounts'

    def handle(self, *args, **kwargs):
        # 1. Ensure the Bank Reserve account exists to fund the interest
        bank_reserve, _ = Account.objects.get_or_create(
            name='CryptoKnights Central Reserve',
            account_type='other',
            defaults={'starting_balance': Decimal('1000000.00')} # The bank's vault
        )

        # 2. Find all eligible savings accounts
        eligible_accounts = Account.objects.filter(
            account_type__in=['savings', 'savingsplus', 'saversplus']
        )
        
        count = 0
        total_interest_paid = Decimal('0.00')

        # 3. Process payouts atomically
        with transaction.atomic():
            for account in eligible_accounts:
                rate = account.get_interest_rate()
                if rate <= Decimal('0.000'):
                    continue
                balance = account.get_balance()
                if balance > Decimal('0.00'):
                    monthly_rate = rate / Decimal('12')
                    interest_amount = balance * monthly_rate
                    interest_amount = interest_amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

                    if interest_amount > Decimal('0.00'):
                        Transaction.objects.create(
                            transaction_type='deposit',
                            amount=interest_amount,
                            from_account=bank_reserve, 
                            to_account=account
                        )
                        count += 1
                        total_interest_paid += interest_amount
                        self.stdout.write(f"Paid £{interest_amount} to {account.name}")

        self.stdout.write(self.style.SUCCESS(
            f'\nSUCCESS: Processed {count} accounts. Total interest paid: £{total_interest_paid}'
        ))