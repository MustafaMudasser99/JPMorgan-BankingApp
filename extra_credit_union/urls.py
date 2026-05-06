"""
URL configuration for extra_credit_union project.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from banking.auth_views import LoginView, UserAccountsView
from banking.template_views import (
    register_api,
    TemplateRegistrationView,
    DashboardView,
    BalanceView,
    SavingsView,
    update_savings_api,
    apply_savers_plus,
    oobe_settings,
    UserManagementView,
    delete_user,
    toggle_roundup,
    toggle_night_savings,
    BankFinancesView,
    bank_finances_summary_json,
    bank_finances_card_json,
)
from banking.login_views import LoginView as WebLoginView, logout_view, api_login
from banking.views import merchant_payment_request, TransactionViewSet, check_payment_status


def smart_entry(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")

urlpatterns = [
    path("", smart_entry, name="smart-entry"),
    path('admin/', admin.site.urls),
    path('api/', include('banking.urls')),
    
    # JWT token authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Auth endpoints with /auth/ prefix (RESTful API convention)
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/register/', register_api, name='auth-register'),
    path('api/auth/user/', UserAccountsView.as_view(), name='user-accounts'),
    path('api/auth/logout/', lambda request: Response({'detail': 'Successfully logged out.'}), name='auth-logout'),
    
    # Same endpoints without /auth/ prefix (matching frontend expectations)
    path('api/login/', LoginView.as_view(), name='api-login'),
    path('api/register/', register_api, name='api-register'),
    path('api/logout/', lambda request: Response({'detail': 'Successfully logged out.'}), name='api-logout'),
    path('api/user/', UserAccountsView.as_view(), name='api-user'),  # Add this to match frontend request
    
    # Web interface routes
    path('banking/login/', WebLoginView.as_view(), name='login'),
    path('banking/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('banking/balance/', BalanceView.as_view(), name='balance-web'),
    path('banking/savings/', SavingsView.as_view(), name='savings'),
    path('banking/apply-savers-plus/', apply_savers_plus, name='apply-savers-plus'),
    path('banking/oobe/', oobe_settings, name='oobe-settings'),
    path('banking/users/', UserManagementView.as_view(), name='user-management'),
    path('banking/finances/', BankFinancesView.as_view(), name='bank-finances'),
    path('banking/api/finances/summary/', bank_finances_summary_json, name='bank-finances-summary'),
    path('banking/api/finances/card/<str:card_number>/', bank_finances_card_json, name='bank-finances-card'),
    path('banking/users/<int:user_id>/delete/', delete_user, name='delete-user'),
    path('banking/logout/', logout_view, name='logout'),
    path('banking/api-login/', api_login, name='api-login-web'),
    
    # Savings API endpoint
    path('banking/api/savings/update/', update_savings_api, name='update-savings-api'),
    path('banking/nfc/', include('banking.nfc_terminal.urls')),
    path('api/v1/provider/pay/', merchant_payment_request, name='merchant_pay'),
    # Merchant/Provider endpoint (Standalone Function)
    path('api/v1/provider/pay/', merchant_payment_request, name='merchant_pay'),

    # User Approval endpoints (ViewSet Actions)
    path('api/transactions/check_pending/', TransactionViewSet.as_view({'get': 'check_pending'}), name='check-pending'),
    path('api/transactions/<int:pk>/finalize_auth/', TransactionViewSet.as_view({'post': 'finalize_auth'}), name='finalize-auth'),
    path('api/v1/provider/status/<int:transaction_id>/', check_payment_status, name='merchant_check_status'),
    path('api/account/toggle-roundup/', toggle_roundup, name='toggle-roundup'),
    path('api/account/toggle-night-savings/', toggle_night_savings, name='toggle-night-savings'),
]
