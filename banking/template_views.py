"""
Template-based registration view that doesn't rely on REST framework.
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.templatetags.static import static
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import Account, Transaction
from decimal import Decimal

class TemplateRegistrationView(View):
    """
    A template-based registration view that handles both GET and POST requests.
    GET: Displays a simple registration form
    POST: Processes the form and creates user + accounts
    """
    template_name = 'banking/register.html'
    
    def get(self, request, *args, **kwargs):
        """
        Return a simple registration form.
        """
        return render(request, self.template_name, {})
    
    def post(self, request, *args, **kwargs):
        """
        Process registration form data and create user + accounts.
        """
        # Extract form data
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        # Validate required fields
        if not username or not password:
            messages.error(request, 'Username and password are required')
            return render(request, self.template_name, {})
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, self.template_name, {})
        
        try:
            # Create the user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create default Current Account
            current_account = Account.objects.create(
                name=f"{first_name or username}'s Current Account",
                starting_balance=Decimal('1000.00'),
                round_up_enabled=False,
                user=user,
                account_type='current'
            )
            
            # Create default Savings Account
            savings_account = Account.objects.create(
                name=f"{first_name or username}'s Savings Account",
                starting_balance=Decimal('0.00'),
                round_up_enabled=True,
                user=user,
                account_type='savings'
            )
            
            # Success message
            messages.success(request, 'Registration successful! Two accounts created.')
            
            # Redirect to login page (or AJAX response for API)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Registration successful',
                    'accounts': [
                        {
                            'id': str(current_account.id),
                            'name': current_account.name,
                            'type': current_account.get_account_type_display(),
                            'balance': str(current_account.starting_balance)
                        },
                        {
                            'id': str(savings_account.id),
                            'name': savings_account.name,
                            'type': savings_account.get_account_type_display(),
                            'balance': str(savings_account.starting_balance)
                        }
                    ]
                })
            return redirect('login')  # Redirect to login page
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return render(request, self.template_name, {})
        
@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    @method_decorator(login_required(login_url='login'))
    def get(self, request):
        accounts = Account.objects.filter(user=request.user)
        total_balance = sum(account.starting_balance for account in accounts)
        recent_transactions = Transaction.objects.filter(
            from_account__in=accounts
        ).select_related('business').order_by('-timestamp')[:10]
        total_savings = sum(account.round_up_pot for account in accounts)

        context = {
            'accounts': accounts,
            'total_balance': total_balance,
            'recent_transactions': recent_transactions,
            'total_savings': total_savings,
        }
        return render(request, 'banking/dashboard.html', context)

# API-style functions that don't require REST framework
def register_api(request):
    """
    Simple API-style registration function that uses Django's HttpResponse.
    """
    if request.method == 'GET':
        return JsonResponse({
            'message': 'Registration API is working. Send a POST request to register.',
            'required_fields': ['username', 'password'],
            'optional_fields': ['email', 'first_name', 'last_name']
        })
    
    elif request.method == 'POST':
        import json
        
        # Parse JSON request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # Extract user data
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        # Validate required fields
        if not username or not password:
            return JsonResponse({'error': 'Username and password are required'}, status=400)
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)
        
        try:
            # Create the user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create default Current Account
            current_account = Account.objects.create(
                name=f"{first_name or username}'s Current Account",
                starting_balance=Decimal('1000.00'),
                round_up_enabled=False,
                user=user,
                account_type='current'
            )
            
            # Create default Savings Account
            savings_account = Account.objects.create(
                name=f"{first_name or username}'s Savings Account",
                starting_balance=Decimal('0.00'),
                round_up_enabled=True,
                user=user,
                account_type='savings'
            )
            
            # Return success response
            return JsonResponse({
                'message': 'User registered successfully',
                'user_id': user.id,
                'accounts': [
                    {
                        'id': str(current_account.id),
                        'name': current_account.name,
                        'type': current_account.get_account_type_display(),
                        'balance': str(current_account.starting_balance)
                    },
                    {
                        'id': str(savings_account.id),
                        'name': savings_account.name,
                        'type': savings_account.get_account_type_display(),
                        'balance': str(savings_account.starting_balance)
                    }
                ]
            }, status=201)
            
        except Exception as e:
            return JsonResponse({'error': f'Error creating user: {str(e)}'}, status=500)
    
    else:
            return JsonResponse({'error': 'Method not allowed'}, status=405)

class BalanceView(View):
        """
        View for displaying account balances, transferring funds, and printing transaction history.
        """
        template_name = 'banking/balance.html'
        
        def get(self, request, *args, **kwargs):
            """
            Display the balance page with account information.
            """
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Get user accounts
            accounts = Account.objects.filter(user=request.user)
            
            # Get recent transactions
            transactions = []
            for account in accounts:
                # Get outgoing transactions
                outgoing_transactions = Transaction.objects.filter(
                    from_account=account
                ).order_by('-timestamp')[:5]
                
                for transaction in outgoing_transactions:
                    transactions.append({
                        'account': account.name,
                        'direction': 'Outgoing',
                        'reference': transaction.transaction_type,
                        'amount': abs(transaction.amount),
                        'status': 'Completed',
                        'date': transaction.timestamp.strftime('%d %b %Y')
                    })
                
                # Get incoming transactions
                incoming_transactions = Transaction.objects.filter(
                    to_account=account
                ).order_by('-timestamp')[:5]
                
                for transaction in incoming_transactions:
                    transactions.append({
                        'account': account.name,
                        'direction': 'Incoming',
                        'reference': transaction.transaction_type,
                        'amount': abs(transaction.amount),
                        'status': 'Completed',
                        'date': transaction.timestamp.strftime('%d %b %Y')
                    })
            
            # Sort transactions by date (newest first)
            transactions = sorted(transactions, key=lambda x: x['date'], reverse=True)
            
            # Calculate total available funds
            total_balance = sum(account.get_balance() for account in accounts)
            
            # Calculate percentages for progress bars
            account_balances = {}
            for account in accounts:
                balance = account.get_balance()
                account_balances[account.name] = {
                    'balance': balance,
                    'percentage': int((balance / total_balance * 100) if total_balance > 0 else 0)
                }
            
            context = {
                'accounts': accounts,
                'transactions': transactions,
                'total_balance': total_balance,
                'account_balances': account_balances,
                'logo_url': static('banking/images/logo.png')
            }
            
            return render(request, self.template_name, context)
        
        def post(self, request, *args, **kwargs):
            """
            Handle fund transfers between accounts.
            """
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            # Determine transfer type
            transfer_type = request.POST.get('transfer_type')
            
            if transfer_type == 'internal':
                # Internal transfer between user's accounts
                from_account_id = request.POST.get('from_account')
                to_account_id = request.POST.get('to_account')
                amount = request.POST.get('amount')
                reference = request.POST.get('reference', 'Internal transfer')
                
                # Validate input
                if not from_account_id or not to_account_id or not amount:
                    return JsonResponse({'error': 'Missing required fields'}, status=400)
                
                try:
                    amount = Decimal(amount)
                    if amount <= 0:
                        return JsonResponse({'error': 'Amount must be positive'}, status=400)
                    
                    # Get accounts
                    from_account = Account.objects.get(id=from_account_id, user=request.user)
                    to_account = Account.objects.get(id=to_account_id, user=request.user)
                    
                    # Check if accounts are different
                    if from_account.id == to_account.id:
                        return JsonResponse({'error': 'Cannot transfer to the same account'}, status=400)
                    
                    # Check sufficient funds
                    if from_account.get_balance() < amount:
                        return JsonResponse({'error': 'Insufficient funds'}, status=400)
                    
                    # Create transaction
                    Transaction.objects.create(
                        transaction_type="transfer",
                        amount=-amount,
                        from_account=from_account,
                        to_account=to_account
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Successfully transferred {amount} from {from_account.name} to {to_account.name}'
                    })
                    
                except Account.DoesNotExist:
                    return JsonResponse({'error': 'Account not found'}, status=404)
                except ValueError:
                    return JsonResponse({'error': 'Invalid amount'}, status=400)
                except Exception as e:
                    return JsonResponse({'error': str(e)}, status=500)
                    
            elif transfer_type == 'external':
                # External transfer to another user's account
                from_account_id = request.POST.get('from_account')
                recipient_name = request.POST.get('recipient_name')
                account_number = request.POST.get('account_number')
                sort_code = request.POST.get('sort_code')
                amount = request.POST.get('amount')
                reference = request.POST.get('reference', 'External transfer')
                
                # Validate input
                if not all([from_account_id, recipient_name, account_number, sort_code, amount]):
                    return JsonResponse({'error': 'Missing required fields'}, status=400)
                
                try:
                    amount = Decimal(amount)
                    if amount <= 0:
                        return JsonResponse({'error': 'Amount must be positive'}, status=400)
                    
                    # Get source account
                    from_account = Account.objects.get(id=from_account_id, user=request.user)
                    
                    # Check sufficient funds
                    if from_account.get_balance() < amount:
                        return JsonResponse({'error': 'Insufficient funds'}, status=400)
                    
                    # Create transaction
                    Transaction.objects.create(
                        transaction_type="payment",
                        amount=-amount,
                        from_account=from_account,
                        to_account=None
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Successfully transferred {amount} to external account {account_number}'
                    })
                    
                except Account.DoesNotExist:
                    return JsonResponse({'error': 'Account not found'}, status=404)
                except ValueError:
                    return JsonResponse({'error': 'Invalid amount'}, status=400)
                except Exception as e:
                    return JsonResponse({'error': str(e)}, status=500)
            
            else:
                return JsonResponse({'error': 'Invalid transfer type'}, status=400)
    
def export_transactions_csv(request):
        """
        Export transactions as CSV file.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        import csv
        from django.http import HttpResponse
        
        # Get user accounts
        accounts = Account.objects.filter(user=request.user)
        
        # Create HttpResponse with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        
        # Create CSV writer
        writer = csv.writer(response)
        writer.writerow(['Account', 'Direction', 'Reference', 'Amount', 'Status', 'Date'])
        
        # Add transaction data
        for account in accounts:
            # Get outgoing transactions
            outgoing_transactions = Transaction.objects.filter(
                from_account=account
            ).order_by('-timestamp')
            
            for transaction in outgoing_transactions:
                writer.writerow([
                    account.name,
                    'Outgoing',
                    transaction.transaction_type,
                    abs(transaction.amount),
                    'Completed',
                    transaction.timestamp.strftime('%d %b %Y')
                ])
            
            # Get incoming transactions
            incoming_transactions = Transaction.objects.filter(
                to_account=account
            ).order_by('-timestamp')
            
            for transaction in incoming_transactions:
                writer.writerow([
                    account.name,
                    'Incoming',
                    transaction.transaction_type,
                    abs(transaction.amount),
                    'Completed',
                    transaction.timestamp.strftime('%d %b %Y')
                ])
        
        return response
