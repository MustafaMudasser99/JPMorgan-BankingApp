from rest_framework import serializers
from .models import Account, Transaction, Business, Card
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = [
            'id', 'account', 'card_holder_name', 'card_number', 
            'expiry_date', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class AccountSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    cards = CardSerializer(many=True, read_only=True)

    class Meta:
        model = Account
        fields = [
            'id', 'name', 'starting_balance', 'round_up_enabled', 
            'postcode', 'user', 'user_details', 'account_type', 
            'account_type_display', 'round_up_pot', 'cards'
        ]
        
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_type', 'amount', 'from_account', 'to_account', 'business', 'timestamp', 'status', 'expires_at']
        read_only_fields = ['id', 'timestamp', 'status', 'expires_at']

class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ['id', 'name', 'category', 'sanctioned']