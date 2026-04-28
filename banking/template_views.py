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
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from .models import Account, Transaction, SavingsTracker
from decimal import Decimal, InvalidOperation
import json
from django.views.decorators.http import require_POST
from .models import Account, Transaction, UserProfile, SavingsTracker

@login_required(login_url='login')
def apply_savers_plus(request):
    if request.method != 'POST':
        return redirect('dashboard')

    if Account.objects.filter(user=request.user, account_type='saversplus').exists():
        messages.error(request, 'You already have a Savers Plus account.')
        return redirect('dashboard')

    Account.objects.create(
        name=f"{request.user.first_name or request.user.username}'s Savers Plus Account",
        starting_balance=Decimal('0.00'),
        round_up_enabled=True,
        user=request.user,
        account_type='saversplus',
    )

    messages.success(request, 'Savers Plus account created.')
    return redirect('dashboard')

@require_POST
@login_required(login_url='login')
def oobe_settings(request):
    """
    Persist the out-of-box experience selections and mark onboarding complete.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    action = (request.POST.get('action') or 'save').strip().lower()
    settings_only = request.POST.get('settings_only') == '1'
    if action == 'skip':
        profile.oobe_completed = True
        profile.selected_account_types = ['current']
        profile.dashboard_widgets = ['overview', 'transactions', 'accounts', 'quick_transfer']
        profile.save(update_fields=['oobe_completed', 'selected_account_types', 'dashboard_widgets', 'updated_at'])
        messages.success(request, 'Setup skipped. You can keep using the app.')
        return redirect('dashboard')

    widgets = request.POST.getlist('widgets') or []
    if 'overview' not in widgets:
        widgets = ['overview', *widgets]

    if settings_only:
        # Settings mode only edits dashboard windows (no account creation/selection changes).
        profile.oobe_completed = True
        profile.dashboard_widgets = widgets
        profile.save(update_fields=['oobe_completed', 'dashboard_widgets', 'updated_at'])
        messages.success(request, 'Your dashboard layout has been updated.')
        return redirect('dashboard')

    open_savings = request.POST.get('open_savings') == 'on'
    open_savers_plus = request.POST.get('open_saversplus') == 'on'
    accept_ads = request.POST.get('accept_ads') == 'on'

    # Account types: current is mandatory.
    selected_types = ['current']
    if open_savings:
        selected_types.append('savings')
    if open_savers_plus:
        if not accept_ads:
            messages.error(request, 'To open Savers Plus you must agree to have an advert displayed.')
            return redirect('dashboard')
        selected_types.append('saversplus')

    # Create optional accounts if selected and not already present.
    user = request.user
    if open_savings and not Account.objects.filter(user=user, account_type='savings').exists():
        Account.objects.create(
            name=f"{user.first_name or user.username}'s Savings Account",
            starting_balance=Decimal('0.00'),
            round_up_enabled=True,
            user=user,
            account_type='savings',
        )

    if open_savers_plus and not Account.objects.filter(user=user, account_type='saversplus').exists():
        Account.objects.create(
            name=f"{user.first_name or user.username}'s Savers Plus Account",
            starting_balance=Decimal('0.00'),
            round_up_enabled=True,
            user=user,
            account_type='saversplus',
        )

    profile.oobe_completed = True
    profile.selected_account_types = selected_types
    profile.dashboard_widgets = widgets
    profile.save(update_fields=['oobe_completed', 'selected_account_types', 'dashboard_widgets', 'updated_at'])

    messages.success(request, 'Your preferences have been saved.')
    return redirect('dashboard')

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
            
            # Default accounts are created by the post_save(User) signal to avoid
            # double-creating them across multiple registration flows.
            accounts = Account.objects.filter(user=user)
            
            # Success message
            messages.success(request, 'Registration successful! Two accounts created.')
            
            # Redirect to login page (or AJAX response for API)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Registration successful',
                    'accounts': [
                        {
                            'id': str(account.id),
                            'name': account.name,
                            'type': account.get_account_type_display(),
                            'balance': str(account.starting_balance)
                        }
                        for account in accounts
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
        if not request.user.is_authenticated:
            return redirect('login')

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        accounts = Account.objects.filter(user=request.user)
        has_savers_plus = accounts.filter(account_type='saversplus').exists()

        # Auto-complete OOBE for existing users who already have optional accounts.
        if not profile.oobe_completed:
            existing_types = set(accounts.values_list('account_type', flat=True))
            if existing_types - {'current'}:
                profile.oobe_completed = True
                profile.selected_account_types = sorted(existing_types)
                profile.dashboard_widgets = ['overview', 'transactions', 'accounts', 'quick_transfer']
                profile.save(update_fields=['oobe_completed', 'selected_account_types', 'dashboard_widgets', 'updated_at'])

        total_balance = sum(account.starting_balance for account in accounts)
        recent_transactions = Transaction.objects.filter(
            from_account__in=accounts
        ).select_related('business').order_by('-timestamp')[:10]
        total_savings = sum(account.round_up_pot for account in accounts)

        context = {
            'accounts': accounts,
            'has_savers_plus': has_savers_plus,
            'total_balance': total_balance,
            'recent_transactions': recent_transactions,
            'total_savings': total_savings,
            'show_oobe': not profile.oobe_completed,
            'oobe_selected_account_types': profile.selected_account_types or ['current'],
            'oobe_dashboard_widgets': profile.dashboard_widgets or ['overview', 'transactions', 'accounts', 'quick_transfer'],
            'savings_interest_rate_percent': f"{(Account.SAVINGS_INTEREST_RATE * 100):.1f}",
            'savers_plus_interest_rate_percent': f"{(Account.SAVERS_PLUS_INTEREST_RATE * 100):.1f}",
        }
        return render(request, 'banking/dashboard.html', context)

@method_decorator(login_required, name='dispatch')
class SavingsView(View):
    template_name = 'banking/savings.html'

    def get(self, request, *args, **kwargs):
        savings_account, _ = Account.objects.get_or_create(
            user=request.user,
            account_type='savings',
            defaults={
                'name': 'My Savings Account',
                'starting_balance': Decimal('0.00'),
            }
        )

        savings_tracker = SavingsTracker.objects.filter(account=savings_account).first()

        return render(request, self.template_name, {
            'savings_tracker': savings_tracker
        })


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def update_savings_api(request):
    try:
        data = json.loads(request.body or "{}")

        savings_account, _ = Account.objects.get_or_create(
            user=request.user,
            account_type='savings',
            defaults={
                'name': 'My Savings Account',
                'starting_balance': Decimal('0.00'),
            }
        )

        if data.get('savings_enabled') is False:
            deleted_count, _ = SavingsTracker.objects.filter(account=savings_account).delete()
            return JsonResponse({
                'success': True,
                'message': 'Savings tracker deleted successfully.',
                'deleted_count': deleted_count,
                'savings_enabled': False,
                'savings_goal': '0.00',
                'progress_percentage': 0
            })

        if data.get('savings_enabled') is True:
            if 'savings_goal' not in data:
                return JsonResponse({
                    'success': False,
                    'error': 'Savings goal is required when enabling savings.'
                }, status=400)

            try:
                savings_goal = Decimal(str(data['savings_goal']))
                if savings_goal <= 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'Savings goal must be greater than 0.'
                    }, status=400)
            except Exception:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid savings goal amount.'
                }, status=400)

            savings_tracker, created = SavingsTracker.objects.update_or_create(
                account=savings_account,
                defaults={
                    'savings_enabled': True,
                    'savings_goal': savings_goal,
                }
            )

            return JsonResponse({
                'success': True,
                'message': 'Savings settings updated successfully.',
                'created': created,
                'savings_enabled': savings_tracker.savings_enabled,
                'current_amount': str(savings_tracker.current_amount),
                'savings_goal': str(savings_tracker.savings_goal),
                'progress_percentage': float(savings_tracker.progress_percentage()),
            })

        return JsonResponse({
            'success': False,
            'error': 'Invalid request.'
        }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

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
            accounts = Account.objects.filter(user=user)
            
            # Return success response
            return JsonResponse({
                'message': 'User registered successfully',
                'user_id': user.id,
                'accounts': [
                    {
                        'id': str(account.id),
                        'name': account.name,
                        'type': account.get_account_type_display(),
                        'balance': str(account.starting_balance)
                    }
                    for account in accounts
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

            account_type_filters = []
            seen_account_types = set()
            for account in accounts:
                if account.account_type in seen_account_types:
                    continue
                seen_account_types.add(account.account_type)
                account_type_filters.append({
                    'key': account.account_type,
                    'label': account.get_account_type_display(),
                })
            
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
            balance_rows = []
            for account in accounts:
                balance = account.get_balance()
                percentage = int((balance / total_balance * 100) if total_balance > 0 else 0)
                balance_rows.append({
                    'name': account.name,
                    'balance': balance,
                    'percentage': percentage,
                    'account_type': account.account_type,
                    'account_type_display': account.get_account_type_display(),
                })
            
            context = {
                'accounts': accounts,
                'transactions': transactions,
                'total_balance': total_balance,
                'balance_rows': balance_rows,
                'logo_url': static('banking/images/logo.png'),
                'account_type_filters': account_type_filters,
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
                        amount=amount,
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
                        amount=amount,
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


@method_decorator(login_required(login_url='login'), name='dispatch')
class UserManagementView(View):
    """
    Staff-only page for listing, creating, and deleting users.
    """
    template_name = 'banking/users.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to manage users.')
            return redirect('dashboard')

        users = User.objects.all().order_by('username')
        return render(request, self.template_name, {'users': users})

    def post(self, request, *args, **kwargs):
        """
        Create a new user (and default accounts) from a simple form.
        """
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to manage users.')
            return redirect('dashboard')

        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        email = (request.POST.get('email') or '').strip()
        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        is_staff = request.POST.get('is_staff') == 'on'

        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return redirect('user-management')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('user-management')

        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            if is_staff:
                user.is_staff = True
                user.save(update_fields=['is_staff'])
            # Default accounts are created by the post_save(User) signal.

            messages.success(request, f'User "{username}" created.')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')

        return redirect('user-management')


@require_POST
@login_required(login_url='login')
def delete_user(request, user_id: int):
    """
    Staff-only user delete (POST-only). Cascades to accounts via FK.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to manage users.')
        return redirect('dashboard')

    if request.user.id == user_id:
        messages.error(request, "You can't delete your own user while logged in.")
        return redirect('user-management')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('user-management')

    username = user.username
    user.delete()
    messages.success(request, f'User "{username}" deleted.')
    return redirect('user-management')
