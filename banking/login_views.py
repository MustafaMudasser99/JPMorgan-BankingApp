"""
Login views for the banking application.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Account
from .serializers import AccountSerializer

class LoginView(View):
    """
    Handle login requests - both web form and API
    """
    def get(self, request):
        """Display login form"""
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, 'banking/login.html')
    
    def post(self, request):
        """Handle login form submission"""
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Please provide both username and password')
            return render(request, 'banking/login.html')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Generate JWT tokens for API access
            refresh = RefreshToken.for_user(user)
            request.session['access_token'] = str(refresh.access_token)
            request.session['refresh_token'] = str(refresh)
            
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'banking/login.html')

def api_login(request):
    """
    API endpoint for login - returns JWT tokens
    """
    if request.method == 'POST':
        import json
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return JsonResponse({'error': 'Username and password required'}, status=400)
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Get user's accounts
            accounts = Account.objects.filter(user=user)
            account_data = AccountSerializer(accounts, many=True).data
            
            return JsonResponse({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'accounts': account_data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            })
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    
    return JsonResponse({
        'message': 'Login API is working. Send a POST request with username and password.',
        'required_fields': ['username', 'password']
    })

def logout_view(request):
    """Handle logout"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('login')