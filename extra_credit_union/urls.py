"""
URL configuration for extra_credit_union project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from banking.auth_views import LoginView, UserAccountsView
from banking.template_views import register_api, TemplateRegistrationView, DashboardView, BalanceView, apply_savers_plus, oobe_settings, UserManagementView, delete_user
from banking.login_views import LoginView as WebLoginView, logout_view, api_login


urlpatterns = [
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
    path('banking/apply-savers-plus/', apply_savers_plus, name='apply-savers-plus'),
    path('banking/oobe/', oobe_settings, name='oobe-settings'),
    path('banking/users/', UserManagementView.as_view(), name='user-management'),
    path('banking/users/<int:user_id>/delete/', delete_user, name='delete-user'),
    path('banking/logout/', logout_view, name='logout'),
    path('banking/api-login/', api_login, name='api-login-web'),
]
