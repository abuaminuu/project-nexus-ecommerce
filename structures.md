Great approach! Your design addresses a common challenge in multi-tenant/multi-app architectures. Let me provide a comprehensive implementation strategy that builds on your ideas while addressing potential challenges:

## 1. Project Structure

```
your_project/
├── manage.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py          # Main URL routing
│   └── wsgi.py
├── apps/
│   ├── __init__.py
│   ├── accounts/        # Central auth app
│   │   ├── models.py    # User, AppProfile, UserAppAccess
│   │   ├── serializers.py
│   │   ├── views.py     # Login, Register, Reset Password
│   │   ├── middleware.py # App routing middleware
│   │   └── tokens.py    # Custom token handling
│   ├── commerce/
│   ├── school/
│   └── logistics/
└── templates/
```

## 2. Core Models (accounts/models.py)

```python
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid

class Application(models.Model):
    """Define available applications"""
    APP_TYPES = (
        ('commerce', 'E-Commerce'),
        ('school', 'School Management'),
        ('logistics', 'Logistics'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=APP_TYPES, unique=True)
    display_name = models.CharField(max_length=100)
    api_base_url = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.display_name

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    is_email_verified = models.BooleanField(default=False)
    
    # Make email the primary identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email

class UserAppProfile(models.Model):
    """Each user can have multiple app profiles"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='app_profiles')
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    app_specific_username = models.CharField(max_length=150, blank=True)
    app_specific_data = models.JSONField(default=dict)  # Store app-specific metadata
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'application']
    
    def __str__(self):
        return f"{self.user.email} - {self.application.name}"

class AppToken(models.Model):
    """App-specific tokens"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='app_tokens')
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    key = models.CharField(max_length=40, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'application']
    
    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)
    
    @staticmethod
    def generate_key():
        """Generate a unique token"""
        return uuid.uuid4().hex + uuid.uuid4().hex
    
    def __str__(self):
        return f"{self.user.email} - {self.application.name} Token"

class PendingRegistration(models.Model):
    """Temporary storage for registration before app selection"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    registration_data = models.JSONField()
    temp_token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def is_valid(self):
        from django.utils import timezone
        return self.expires_at > timezone.now()
```

## 3. Authentication Views (accounts/views.py)

```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
import secrets
import hashlib

from .models import User, Application, UserAppProfile, AppToken, PendingRegistration
from .serializers import (
    RegistrationSerializer, AppSelectionSerializer,
    LoginSerializer, PasswordResetSerializer
)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Step 1: Initial registration
    Creates user account but doesn't activate until app selection
    """
    serializer = RegistrationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user exists
    if User.objects.filter(email=serializer.validated_data['email']).exists():
        return Response({
            'message': 'User with this email already exists. Please login.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create temporary registration
    temp_token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(minutes=30)
    
    pending = PendingRegistration.objects.create(
        email=serializer.validated_data['email'],
        registration_data=serializer.validated_data,
        temp_token=temp_token,
        expires_at=expires_at
    )
    
    # Return token for app selection
    return Response({
        'message': 'Please select applications to access',
        'temp_token': temp_token,
        'expires_in': 30  # minutes
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def select_applications(request):
    """
    Step 2: User selects which apps they want to access
    """
    serializer = AppSelectionSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    temp_token = serializer.validated_data['temp_token']
    selected_apps = serializer.validated_data['applications']
    
    # Verify temporary registration
    try:
        pending = PendingRegistration.objects.get(
            temp_token=temp_token,
            expires_at__gt=timezone.now()
        )
    except PendingRegistration.DoesNotExist:
        return Response({
            'error': 'Invalid or expired registration session'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create actual user
    user_data = pending.registration_data
    user = User.objects.create_user(
        email=user_data['email'],
        username=user_data.get('username', user_data['email']),
        password=user_data['password'],
        first_name=user_data.get('first_name', ''),
        last_name=user_data.get('last_name', '')
    )
    
    # Create app profiles and tokens for selected apps
    apps = Application.objects.filter(name__in=selected_apps, is_active=True)
    
    for app in apps:
        # Create profile
        UserAppProfile.objects.create(
            user=user,
            application=app,
            app_specific_username=f"{user.email.split('@')[0]}_{app.name}"
        )
        
        # Create app-specific token
        AppToken.objects.create(
            user=user,
            application=app
        )
    
    # Clean up pending registration
    pending.delete()
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'message': 'Registration successful',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'email': user.email,
            'id': user.id,
            'applications': [app.name for app in apps]
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login with app context
    """
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    app_name = serializer.validated_data.get('app_name')  # Optional
    
    # Authenticate user
    user = authenticate(request, username=email, password=password)
    
    if not user or not user.is_active:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Get user's apps
    user_apps = UserAppProfile.objects.filter(
        user=user, 
        is_active=True,
        application__is_active=True
    ).select_related('application')
    
    app_list = [{
        'name': profile.application.name,
        'display_name': profile.application.display_name,
        'has_token': AppToken.objects.filter(
            user=user, 
            application=profile.application,
            is_active=True
        ).exists()
    } for profile in user_apps]
    
    # If specific app requested, generate token for it
    tokens = {}
    if app_name:
        try:
            app = Application.objects.get(name=app_name, is_active=True)
            app_token = AppToken.objects.get(
                user=user, 
                application=app,
                is_active=True
            )
            app_token.last_used = timezone.now()
            app_token.save()
            
            tokens['app_token'] = app_token.key
        except (Application.DoesNotExist, AppToken.DoesNotExist):
            pass
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    # Add app context to JWT token
    refresh['app_context'] = app_name
    
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'email': user.email,
            'id': user.id,
            'name': f"{user.first_name} {user.last_name}".strip() or user.email,
            'apps': app_list
        },
        'tokens': tokens
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    Password reset request
    """
    serializer = PasswordResetSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    
    # Always return same response for security
    response_msg = {
        'message': 'If your email exists, you will receive reset instructions'
    }
    
    try:
        user = User.objects.get(email=email, is_active=True)
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        hashed_token = hashlib.sha256(reset_token.encode()).hexdigest()
        
        # Store in session/cache (implement your token storage)
        # ...
        
        # Send email with reset link
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        # Send email logic here
        # ...
        
    except User.DoesNotExist:
        pass
    
    return Response(response_msg, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_app_token(request):
    """
    Get or refresh app-specific token
    """
    app_name = request.data.get('app_name')
    
    if not app_name:
        return Response({
            'error': 'app_name required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        app = Application.objects.get(name=app_name, is_active=True)
        app_token, created = AppToken.objects.get_or_create(
            user=request.user,
            application=app,
            defaults={'is_active': True}
        )
        
        if not app_token.is_active:
            return Response({
                'error': 'Token is inactive for this application'
            }, status=status.HTTP_403_FORBIDDEN)
        
        app_token.last_used = timezone.now()
        app_token.save()
        
        return Response({
            'app_name': app_name,
            'token': app_token.key,
            'created': app_token.created,
            'expires_at': app_token.expires_at
        }, status=status.HTTP_200_OK)
        
    except Application.DoesNotExist:
        return Response({
            'error': 'Invalid application'
        }, status=status.HTTP_400_BAD_REQUEST)
```

## 4. Middleware for App Routing

```python
# accounts/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve, reverse
from django.shortcuts import redirect
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import UserAppProfile, AppToken

class AppRoutingMiddleware(MiddlewareMixin):
    """
    Middleware to route users to their subscribed apps
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # App URL prefixes mapping
        self.app_urls = {
            'commerce': '/api/commerce/',
            'school': '/api/school/',
            'logistics': '/api/logistics/',
        }
    
    def process_request(self, request):
        # Skip for non-API routes
        if not request.path.startswith('/api/'):
            return None
        
        # Extract app context from JWT token
        app_context = self.get_app_context_from_token(request)
        
        if app_context:
            request.app_context = app_context
            
            # Validate user has access to this app
            if not self.validate_app_access(request, app_context):
                from django.http import JsonResponse
                return JsonResponse({
                    'error': f'Access denied to {app_context} application'
                }, status=403)
            
            # Add app-specific headers
            request.META['HTTP_X_APP_CONTEXT'] = app_context
            
            # You could also rewrite paths here if needed
            # if request.path.startswith('/api/'):
            #     request.path_info = f'/api/{app_context}' + request.path[4:]
        
        return None
    
    def get_app_context_from_token(self, request):
        """Extract app context from JWT token"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)
                return validated_token.get('app_context')
            except:
                pass
        
        # Also check for app token in headers
        app_token_key = request.META.get('HTTP_X_APP_TOKEN')
        if app_token_key:
            try:
                app_token = AppToken.objects.select_related('application').get(
                    key=app_token_key,
                    is_active=True
                )
                return app_token.application.name
            except AppToken.DoesNotExist:
                pass
        
        return None
    
    def validate_app_access(self, request, app_context):
        """Check if user has access to the requested app"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False
        
        return UserAppProfile.objects.filter(
            user=request.user,
            application__name=app_context,
            is_active=True
        ).exists()


class AppTokenAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate using app-specific tokens
    """
    
    def process_request(self, request):
        app_token_key = request.META.get('HTTP_X_APP_TOKEN')
        
        if app_token_key and not request.user.is_authenticated:
            try:
                app_token = AppToken.objects.select_related('user', 'application').get(
                    key=app_token_key,
                    is_active=True
                )
                
                # Check if token expired
                if app_token.expires_at and app_token.expires_at < timezone.now():
                    return None
                
                # Authenticate user
                request.user = app_token.user
                request.app_context = app_token.application.name
                
                # Update last used
                app_token.last_used = timezone.now()
                app_token.save()
                
            except AppToken.DoesNotExist:
                pass
        
        return None
```

## 5. Serializers

```python
# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Application

class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': "Passwords do not match"
            })
        return data
    
    def validate_email(self, value):
        return value.lower().strip()

class AppSelectionSerializer(serializers.Serializer):
    temp_token = serializers.CharField()
    applications = serializers.ListField(
        child=serializers.ChoiceField(choices=Application.APP_TYPES)
    )

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    app_name = serializers.ChoiceField(
        choices=Application.APP_TYPES,
        required=False,
        allow_null=True
    )
    
    def validate_email(self, value):
        return value.lower().strip()

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        return value.lower().strip()
```

## 6. URL Configuration

```python
# config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    
    # App-specific routes
    path('api/commerce/', include('apps.commerce.urls')),
    path('api/school/', include('apps.school.urls')),
    path('api/logistics/', include('apps.logistics.urls')),
]

# apps/accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('select-apps/', views.select_applications, name='select-apps'),
    path('login/', views.login, name='login'),
    path('password-reset/', views.request_password_reset, name='password-reset'),
    path('get-app-token/', views.get_app_token, name='get-app-token'),
]
```

## 7. Settings Configuration

```python
# config/settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # Local apps
    'apps.accounts',
    'apps.commerce',
    'apps.school',
    'apps.logistics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.accounts.middleware.AppTokenAuthenticationMiddleware',  # Add this
    'apps.accounts.middleware.AppRoutingMiddleware',  # Add this
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Application definitions
APPLICATIONS = {
    'commerce': {
        'display_name': 'E-Commerce',
        'api_base': '/api/commerce/',
        'token_expiry': 30,  # days
    },
    'school': {
        'display_name': 'School Management',
        'api_base': '/api/school/',
        'token_expiry': 30,
    },
    'logistics': {
        'display_name': 'Logistics',
        'api_base': '/api/logistics/',
        'token_expiry': 30,
    }
}
```

## 8. App-Specific Usage Example

```python
# apps/commerce/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """
    Commerce app dashboard - uses app context from middleware
    """
    # Access app context from request
    app_context = getattr(request, 'app_context', None)
    
    # Or from headers
    app_context = request.META.get('HTTP_X_APP_CONTEXT')
    
    # User's app-specific profile
    app_profile = request.user.app_profiles.get(
        application__name='commerce'
    )
    
    return Response({
        'message': f'Welcome to {app_context} dashboard',
        'user': request.user.email,
        'app_username': app_profile.app_specific_username,
        'app_data': app_profile.app_specific_data
    })

# apps/commerce/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
```

## 9. Client Usage Examples

```javascript
// Registration flow
async function register() {
    // Step 1: Register
    const regResponse = await fetch('/api/auth/register/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            email: 'user@example.com',
            password: 'SecurePass123!',
            confirm_password: 'SecurePass123!'
        })
    });
    
    const regData = await regResponse.json();
    
    // Step 2: Select apps
    const appResponse = await fetch('/api/auth/select-apps/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            temp_token: regData.temp_token,
            applications: ['commerce', 'school']
        })
    });
    
    return await appResponse.json();
}

// Login with app context
async function login(appName = 'commerce') {
    const response = await fetch('/api/auth/login/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            email: 'user@example.com',
            password: 'SecurePass123!',
            app_name: appName
        })
    });
    
    const data = await response.json();
    
    // Store tokens
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    
    if (data.tokens.app_token) {
        localStorage.setItem('app_token', data.tokens.app_token);
    }
    
    return data;
}

// Access app-specific API
async function accessAppAPI(appName, endpoint) {
    const token = localStorage.getItem('access_token');
    const appToken = localStorage.getItem('app_token');
    
    const response = await fetch(`/api/${appName}/${endpoint}`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-App-Token': appToken,
            'X-App-Context': appName
        }
    });
    
    return await response.json();
}
```

## 10. Management Command to Initialize Apps

```python
# apps/accounts/management/commands/init_apps.py
from django.core.management.base import BaseCommand
from apps.accounts.models import Application

class Command(BaseCommand):
    help = 'Initialize applications'

    def handle(self, *args, **options):
        apps = [
            {'name': 'commerce', 'display_name': 'E-Commerce', 'api_base_url': '/api/commerce/'},
            {'name': 'school', 'display_name': 'School Management', 'api_base_url': '/api/school/'},
            {'name': 'logistics', 'display_name': 'Logistics', 'api_base_url': '/api/logistics/'},
        ]
        
        for app_data in apps:
            app, created = Application.objects.get_or_create(
                name=app_data['name'],
                defaults={
                    'display_name': app_data['display_name'],
                    'api_base_url': app_data['api_base_url']
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created application: {app.display_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Application already exists: {app.display_name}')
                )
```

## Key Advantages of This Approach:

1. **Centralized Authentication**: Single auth system for all apps
2. **App-Specific Tokens**: Separate tokens per application
3. **Flexible User Onboarding**: Users choose apps after registration
4. **Context-Aware Middleware**: Routes requests based on app context
5. **Scalable**: Easy to add new applications
6. **Security**: App-level access control
7. **Free Hosting Friendly**: Single Django project, multiple apps

This design allows you to host everything on free tiers while maintaining separation of concerns between different applications.

