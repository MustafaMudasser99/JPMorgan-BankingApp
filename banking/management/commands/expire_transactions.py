from django.core.management.base import BaseCommand
from django.utils import timezone
from banking.models import Transaction

class Command(BaseCommand):
    help = 'Expires pending transactions that have exceeded their 5-minute window'

    def handle(self, *args, **kwargs):
        # Find all pending transactions that have an expiry time in the past
        expired_count = Transaction.objects.filter(
            status='pending',
            expires_at__lt=timezone.now()
        ).update(status='expired')

        if expired_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully expired {expired_count} transactions.'))
        else:
            self.stdout.write('No expired transactions found.')