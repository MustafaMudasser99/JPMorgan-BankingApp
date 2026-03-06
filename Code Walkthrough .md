# Banking Application Code Walkthrough Guide

Based on my analysis of the codebase, here's a comprehensive breakdown of how the banking application works, perfect for explaining to other developers during a code walkthrough.

## **1. Architecture Overview**

**Tech Stack:**
- **Backend**: Django REST Framework (DRF) with Python
- **Database**: SQLite (default Django DB)
- **Authentication**: JWT (JSON Web Tokens) using `djangorestframework-simplejwt`
- **API Documentation**: Swagger/Redoc via `drf-yasg`
- **Containerization**: Docker with Docker Compose

**Project Structure:**
```
Team7BankingApp/
├── banking/                    # Main Django app
│   ├── models.py              # Database models
│   ├── views.py               # API views and business logic
│   ├── serializers.py         # Data serializers
│   ├── urls.py                # App URL routing
│   ├── auth_views.py          # Authentication views
│   ├── template_views.py     # Template-based views (HTML)
│   └── tests.py               # Comprehensive test suite
├── extra_credit_union/        # Django project settings
└── docker-compose.yml          # Container orchestration
```

## **2. Core Data Models**

### **Account Model** (`banking/models.py`)
```python
class Account(models.Model):
    ACCOUNT_TYPES = [
        ('current', 'Current'),
        ('savings', 'Savings'),
        ('credit', 'Credit'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    starting_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    round_up_enabled = models.BooleanField(default=False)
    postcode = models.CharField(max_length=10, null=True, blank=True)
    round_up_pot = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts', null=True, blank=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='current')
```
**Key Features:**
- UUID primary keys for security
- Support for multiple account types (current, savings, credit)
- Round-up feature with separate "pot" tracking
- User association via ForeignKey to Django's User model

### **Transaction Model**
```python
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
```
**Key Features:**
- Comprehensive transaction type system
- Business association for spending categorization
- Automatic timestamping
- Bidirectional relationships (from_account/to_account)

### **Business Model**
```python
class Business(models.Model):
    id = models.CharField(primary_key=True, max_length=50)  # e.g., "kfc", "tesco"
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    sanctioned = models.BooleanField(default=False)
```
**Purpose:** Track business entities for transaction categorization and sanction monitoring.

## **3. API Endpoints & Authentication**

### **Authentication System**
- **JWT-based authentication** using `djangorestframework-simplejwt`
- **Login**: `POST /api/auth/login/` - Returns JWT tokens + user accounts
- **Registration**: `POST /api/auth/register/` - Creates user + default accounts
- **Token Refresh**: `POST /api/token/refresh/`
- **User Profile**: `GET /api/auth/user/` - Returns authenticated user data

### **Main API Endpoints** (`banking/urls.py`)
```
/api/accounts/              # Account CRUD operations
/api/transactions/         # Transaction management
/api/businesses/           # Business management
/api/auth/login/           # User authentication
/api/auth/register/        # User registration
/api/auth/user/            # Current user profile
/api/swagger/              # Swagger UI documentation
/api/redoc/                # ReDoc documentation
```

### **ViewSets & Permissions**
- **AccountViewSet**: User-specific account access with admin overrides
- **TransactionViewSet**: Transaction operations with ownership validation
- **BusinessViewSet**: Business management with admin-only write access
- **Permission System**: 
  - `IsAuthenticated` for regular users
  - `IsAdminUser` for admin operations
  - `AllowAny` for registration/login

## **4. Key Business Features**

### **Round-Up Feature**
- **Enable/Disable**: `POST /api/accounts/{id}/enable_roundup/`
- **Reclaim Round-Ups**: `POST /api/accounts/{id}/reclaim_roundup/`
- **Round-Up Pot**: Separate field tracking accumulated round-ups

### **Analytics & Reporting**
- **Spending Trends**: `GET /api/transactions/spending-summary/{account_id}/`
- **Top 10 Spenders**: `GET /api/transactions/top-10-spenders/` (admin only)
- **Sanctioned Business Report**: `GET /api/transactions/sanctioned-business-report/` (admin only)

### **User Account Management**
- **Auto-account creation**: New users get Current (£1000) + Savings (£0) accounts
- **Account filtering**: Users only see their own accounts (admins see all)
- **Balance tracking**: Starting balance + transaction calculations

## **5. Security Features**

### **Data Protection**
- UUID primary keys instead of sequential IDs
- User isolation: Users can only access their own accounts/transactions
- Admin-only endpoints for sensitive operations

### **Authentication & Authorization**
- JWT tokens with refresh capability
- Permission classes on all endpoints
- Ownership validation on transaction creation

### **Business Logic Security**
- Sanctioned business tracking
- Transaction validation (user owns from_account)
- Round-up calculations protected from manipulation

## **6. Testing Strategy** (`banking/tests.py`)

### **Test Categories:**
1. **Authentication Tests**: User registration, login, token validation
2. **Account Tests**: CRUD operations, permission checks
3. **Transaction Tests**: Creation, validation, ownership
4. **Business Logic Tests**: Round-up features, spending analytics
5. **Admin Tests**: Manager-specific functionality

### **Test Structure:**
- Uses Django's `APITestCase`
- JWT token authentication in test setup
- Comprehensive edge case coverage
- Task-based organization (TASK3, TASK4, TASK5 comments)

## **7. Deployment & Containerization**

### **Docker Setup**
- **Dockerfile**: Python 3.12 base with requirements installation
- **docker-compose.yml**: Volume mounting for development
- **Port Mapping**: `8000:8000` for local access

### **Development Workflow**
- Volume mounting (`./:/app`) enables live code changes
- SQLite database for simplicity
- Easy local testing with `docker-compose up`

## **8. Code Quality & Documentation**

### **API Documentation**
- **Swagger UI**: Interactive API testing at `/api/swagger/`
- **ReDoc**: Alternative documentation at `/api/redoc/`
- **Auto-generated schemas** from DRF serializers

### **Code Organization**
- Clear separation of concerns (models, views, serializers)
- Comprehensive docstrings and comments
- Task-based implementation markers (`#TASK1`, `#TASK2`, etc.)

## **9. Key Design Patterns**

### **Model-View-Serializer (MVS)**
- Models define data structure
- Views handle business logic
- Serializers transform data for API

### **Permission-Based Access Control**
- Role-based permissions (user vs admin)
- Object-level permissions (user owns their data)
- Granular control per endpoint

### **RESTful API Design**
- Resource-based URLs (`/api/accounts/`, `/api/transactions/`)
- HTTP method semantics (GET, POST, PUT, DELETE)
- Consistent error responses
