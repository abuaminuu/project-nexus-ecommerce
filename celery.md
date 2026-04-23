Excellent choice! Celery is perfect for handling background jobs in your multi-app Django project. Here's a comprehensive implementation:

## 1. Project Structure with Celery

```
your_project/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── celery.py           # Celery app configuration
│   └── urls.py
├── apps/
│   ├── __init__.py
│   ├── accounts/
│   │   ├── tasks.py        # Accounts app tasks
│   │   ├── signals.py
│   │   └── models.py
│   ├── commerce/
│   │   ├── tasks.py        # Commerce app tasks
│   │   └── models.py
│   ├── school/
│   │   ├── tasks.py        # School app tasks
│   │   └── models.py
│   └── logistics/
│       ├── tasks.py        # Logistics app tasks
│       └── models.py
├── docker-compose.yml       # For local development with Redis/RabbitMQ
└── requirements.txt
```

## 2. Celery Configuration

```python
# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('your_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# config/__init__.py
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)
```

## 3. Settings Configuration

```python
# config/settings.py

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Celery Beat Schedule (for periodic tasks)
CELERY_BEAT_SCHEDULE = {
    'clean-expired-tokens': {
        'task': 'apps.accounts.tasks.clean_expired_tokens',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    'send-newsletter': {
        'task': 'apps.commerce.tasks.send_newsletter',
        'schedule': crontab(hour=9, minute=0, day_of_week='mon'),  # Monday 9 AM
    },
    'generate-weekly-reports': {
        'task': 'apps.school.tasks.generate_weekly_reports',
        'schedule': crontab(hour=23, minute=59, day_of_week='sun'),  # Sunday 11:59 PM
    },
    'cleanup-old-logs': {
        'task': 'apps.accounts.tasks.cleanup_old_logs',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'send-reminder-emails': {
        'task': 'apps.logistics.tasks.send_reminder_emails',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
}

# Task routing (optional - for different queues)
CELERY_TASK_ROUTES = {
    'apps.accounts.tasks.*': {'queue': 'accounts'},
    'apps.commerce.tasks.*': {'queue': 'commerce'},
    'apps.school.tasks.*': {'queue': 'school'},
    'apps.logistics.tasks.*': {'queue': 'logistics'},
    'apps.accounts.tasks.email.*': {'queue': 'emails'},  # Email-specific queue
}

# Task execution settings
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_RETRY_DELAY = 60  # 1 minute between retries

# Task result settings
CELERY_RESULT_EXPIRES = 60 * 60 * 24  # 24 hours
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SEND_SENT_EVENT = True

# Celery worker settings
CELERY_WORKER_CONCURRENCY = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
```

## 4. Base Task Classes

```python
# apps/accounts/tasks.py (base tasks)
from celery import Task
from celery.utils.log import get_task_logger
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
import traceback

logger = get_task_logger(__name__)

class BaseTaskWithRetry(Task):
    """Base task class with common retry logic"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failures"""
        logger.error(f'Task {self.name} failed: {exc}\n{traceback.format_exc()}')
        super().on_failure(exc, task_id, args, kwargs, einfo)


class EmailTask(BaseTaskWithRetry):
    """Base task for email operations"""
    
    def send_email(self, subject, template, context, recipient_list):
        """Send email with error handling"""
        try:
            html_message = render_to_string(f'emails/{template}.html', context)
            text_message = render_to_string(f'emails/{template}.txt', context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False
            )
            logger.info(f'Email sent to {recipient_list[0]}: {subject}')
            return True
            
        except Exception as e:
            logger.error(f'Failed to send email to {recipient_list[0]}: {str(e)}')
            raise self.retry(exc=e)
```

## 5. Accounts App Tasks

```python
# apps/accounts/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
import logging

from .models import User, PasswordResetToken, AppToken, UserActivityLog, LoginLog
from .signals import user_registered, user_app_selected

logger = get_task_logger(__name__)

@shared_task(bind=True, base=EmailTask)
def send_welcome_email(self, user_id):
    """Send welcome email to new user"""
    try:
        user = User.objects.get(id=user_id)
        
        context = {
            'user': user,
            'site_name': settings.SITE_NAME,
            'login_url': f"{settings.FRONTEND_URL}/login",
        }
        
        self.send_email(
            subject=f"Welcome to {settings.SITE_NAME}!",
            template='welcome',
            context=context,
            recipient_list=[user.email]
        )
        
        logger.info(f"Welcome email sent to {user.email}")
        return True
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return False


@shared_task(bind=True, base=EmailTask)
def send_password_reset_email(self, user_id, reset_token):
    """Send password reset email"""
    try:
        user = User.objects.get(id=user_id)
        
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'expiry_hours': 1,
            'site_name': settings.SITE_NAME,
        }
        
        self.send_email(
            subject=f"Password Reset Request - {settings.SITE_NAME}",
            template='password_reset',
            context=context,
            recipient_list=[user.email]
        )
        
        logger.info(f"Password reset email sent to {user.email}")
        return True
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return False


@shared_task
def clean_expired_tokens():
    """Clean up expired password reset tokens and old app tokens"""
    # Clean password reset tokens
    expired_reset_tokens = PasswordResetToken.objects.filter(
        expires_at__lt=timezone.now()
    )
    reset_count = expired_reset_tokens.count()
    expired_reset_tokens.delete()
    
    # Clean expired app tokens
    expired_app_tokens = AppToken.objects.filter(
        expires_at__lt=timezone.now(),
        is_active=True
    )
    app_count = expired_app_tokens.count()
    expired_app_tokens.update(is_active=False)
    
    logger.info(f"Cleaned {reset_count} expired reset tokens and {app_count} app tokens")
    return reset_count + app_count


@shared_task
def cleanup_old_logs(days=90):
    """Delete logs older than specified days"""
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Clean activity logs
    activity_count = UserActivityLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    # Clean login logs
    login_count = LoginLog.objects.filter(
        login_time__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned {activity_count} activity logs and {login_count} login logs")
    return activity_count + login_count


@shared_task
def process_app_selection(user_id, selected_apps):
    """Process app selection in background"""
    try:
        user = User.objects.get(id=user_id)
        
        # Initialize each selected app
        for app_name in selected_apps:
            initialize_app_data.delay(user_id, app_name)
        
        # Send confirmation email
        context = {
            'user': user,
            'selected_apps': selected_apps,
            'site_name': settings.SITE_NAME,
        }
        
        html_message = render_to_string('emails/app_selection.html', context)
        
        send_mail(
            subject=f"Applications Selected - {settings.SITE_NAME}",
            message=f"You've selected access to: {', '.join(selected_apps)}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True
        )
        
        logger.info(f"Processed app selection for user {user.email}")
        return True
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return False


@shared_task
def initialize_app_data(user_id, app_name):
    """Initialize app-specific data for user"""
    # This will be overridden by specific app tasks
    logger.info(f"Initializing {app_name} data for user {user_id}")
    return True


@shared_task
def send_login_alert(user_id, ip_address, user_agent):
    """Send alert for new login from unknown device"""
    try:
        user = User.objects.get(id=user_id)
        
        context = {
            'user': user,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'time': timezone.now(),
            'site_name': settings.SITE_NAME,
        }
        
        html_message = render_to_string('emails/login_alert.html', context)
        
        send_mail(
            subject=f"New Login Alert - {settings.SITE_NAME}",
            message=f"A new login was detected from {ip_address}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True
        )
        
        logger.info(f"Login alert sent to {user.email}")
        return True
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return False
```

## 6. Commerce App Tasks

```python
# apps/commerce/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
import json

from .models import Order, Cart, Product, UserPreferences

logger = get_task_logger(__name__)

@shared_task
def process_order(order_id):
    """Process order in background"""
    try:
        from .models import Order
        order = Order.objects.get(id=order_id)
        
        logger.info(f"Processing order {order_id} for user {order.user.email}")
        
        # Update order status
        order.status = 'processing'
        order.save()
        
        # Process payment
        process_payment.delay(order_id)
        
        # Update inventory
        update_inventory.delay(order_id)
        
        # Send confirmation email
        send_order_confirmation.delay(order_id)
        
        # Track for analytics
        track_order_completion.delay(order_id)
        
        logger.info(f"Order {order_id} processing initiated")
        return True
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return False


@shared_task
def process_payment(order_id):
    """Process payment for order"""
    try:
        from .models import Order
        order = Order.objects.get(id=order_id)
        
        logger.info(f"Processing payment for order {order_id}")
        
        # Simulate payment processing
        # In production, integrate with payment gateway
        
        order.payment_status = 'completed'
        order.save()
        
        logger.info(f"Payment completed for order {order_id}")
        return True
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return False


@shared_task
def update_inventory(order_id):
    """Update inventory after order"""
    try:
        from .models import Order, Product
        order = Order.objects.get(id=order_id)
        
        for item in order.items.all():
            product = item.product
            product.stock -= item.quantity
            product.save()
            
            logger.info(f"Updated inventory for {product.name}: new stock {product.stock}")
        
        return True
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return False


@shared_task(bind=True, base=EmailTask)
def send_order_confirmation(self, order_id):
    """Send order confirmation email"""
    try:
        from .models import Order
        order = Order.objects.select_related('user').get(id=order_id)
        
        context = {
            'order': order,
            'user': order.user,
            'site_name': settings.SITE_NAME,
        }
        
        self.send_email(
            subject=f"Order Confirmation #{order.id} - {settings.SITE_NAME}",
            template='order_confirmation',
            context=context,
            recipient_list=[order.user.email]
        )
        
        logger.info(f"Order confirmation sent for order {order_id}")
        return True
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return False


@shared_task
def track_order_completion(order_id):
    """Track order for analytics"""
    try:
        from .models import Order
        order = Order.objects.get(id=order_id)
        
        # Send to analytics service
        analytics_data = {
            'order_id': str(order.id),
            'user_id': str(order.user.id),
            'total': float(order.total),
            'items': [{'product_id': str(item.product.id), 'quantity': item.quantity} 
                     for item in order.items.all()],
            'timestamp': timezone.now().isoformat()
        }
        
        # Here you would send to your analytics service
        # analytics_client.track('order_completed', analytics_data)
        
        logger.info(f"Order {order_id} tracked for analytics")
        return analytics_data
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return False


@shared_task
def send_abandoned_cart_reminders():
    """Send reminders for abandoned carts"""
    from .models import Cart
    
    # Find carts older than 24 hours but not completed
    cutoff = timezone.now() - timedelta(hours=24)
    abandoned_carts = Cart.objects.filter(
        created_at__lt=cutoff,
        is_abandoned=False,
        order__isnull=True
    )
    
    for cart in abandoned_carts:
        # Mark as abandoned
        cart.is_abandoned = True
        cart.save()
        
        # Send reminder email
        send_cart_reminder_email.delay(cart.id)
        
        logger.info(f"Abandoned cart reminder queued for cart {cart.id}")
    
    return abandoned_carts.count()


@shared_task(bind=True, base=EmailTask)
def send_cart_reminder_email(self, cart_id):
    """Send cart reminder email"""
    try:
        from .models import Cart
        cart = Cart.objects.select_related('user').get(id=cart_id)
        
        if not cart.items.exists():
            return False
        
        context = {
            'cart': cart,
            'user': cart.user,
            'items': cart.items.all()[:5],
            'item_count': cart.items.count(),
            'cart_url': f"{settings.FRONTEND_URL}/cart/{cart.id}",
            'site_name': settings.SITE_NAME,
        }
        
        self.send_email(
            subject=f"Complete Your Purchase - Items Waiting in Your Cart",
            template='cart_reminder',
            context=context,
            recipient_list=[cart.user.email]
        )
        
        logger.info(f"Cart reminder sent for cart {cart_id}")
        return True
        
    except Cart.DoesNotExist:
        logger.error(f"Cart {cart_id} not found")
        return False


@shared_task
def send_newsletter():
    """Send newsletter to subscribed users"""
    from apps.accounts.models import User, NotificationSettings
    
    # Get users subscribed to marketing emails
    subscribed_users = User.objects.filter(
        notification_settings__email_marketing=True,
        is_active=True
    )
    
    for user in subscribed_users:
        send_newsletter_to_user.delay(user.id)
    
    logger.info(f"Newsletter queued for {subscribed_users.count()} users")
    return subscribed_users.count()


@shared_task(bind=True, base=EmailTask)
def send_newsletter_to_user(self, user_id):
    """Send newsletter to individual user"""
    try:
        from apps.accounts.models import User
        user = User.objects.get(id=user_id)
        
        context = {
            'user': user,
            'site_name': settings.SITE_NAME,
            'unsubscribe_url': f"{settings.FRONTEND_URL}/unsubscribe",
        }
        
        self.send_email(
            subject=f"Newsletter - {settings.SITE_NAME}",
            template='newsletter',
            context=context,
            recipient_list=[user.email]
        )
        
        logger.info(f"Newsletter sent to {user.email}")
        return True
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return False


@shared_task
def generate_sales_report():
    """Generate daily sales report"""
    from .models import Order
    from django.db.models import Sum, Count
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # Aggregate sales data
    sales_data = Order.objects.filter(
        created_at__date=yesterday,
        status='completed'
    ).aggregate(
        total_sales=Sum('total'),
        order_count=Count('id')
    )
    
    report = {
        'date': yesterday.isoformat(),
        'total_sales': float(sales_data['total_sales'] or 0),
        'order_count': sales_data['order_count'],
        'average_order_value': float(sales_data['total_sales'] or 0) / max(sales_data['order_count'], 1)
    }
    
    # Save or send report
    logger.info(f"Sales report generated: {report}")
    
    # Send to admins
    send_sales_report_email.delay(report)
    
    return report
```

## 7. School App Tasks

```python
# apps/school/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from datetime import timedelta

logger = get_task_logger(__name__)

@shared_task
def generate_weekly_reports():
    """Generate weekly reports for all classes"""
    from .models import Class, Student, Attendance, Grade
    
    logger.info("Generating weekly reports")
    
    last_week = timezone.now() - timedelta(days=7)
    
    for class_obj in Class.objects.filter(is_active=True):
        # Generate class report
        report_data = {
            'class_name': class_obj.name,
            'total_students': class_obj.students.count(),
            'attendance_rate': calculate_attendance_rate(class_obj, last_week),
            'average_grade': calculate_average_grade(class_obj),
            'pending_assignments': class_obj.assignments.filter(
                due_date__gte=timezone.now()
            ).count(),
        }
        
        # Send report to teacher
        send_class_report_email.delay(class_obj.teacher.id, report_data)
        
        logger.info(f"Report generated for class {class_obj.name}")
    
    return True


@shared_task
def send_attendance_reminders():
    """Send reminders for attendance marking"""
    from .models import Class, Teacher
    
    now = timezone.now()
    
    # Find classes starting in 1 hour
    upcoming_classes = Class.objects.filter(
        start_time__gte=now + timedelta(minutes=55),
        start_time__lte=now + timedelta(minutes=65)
    )
    
    for class_obj in upcoming_classes:
        send_attendance_reminder_to_teacher.delay(
            class_obj.teacher.id,
            class_obj.id
        )
    
    return upcoming_classes.count()


@shared_task
def process_bulk_enrollment(enrollment_data):
    """Process bulk student enrollment"""
    from .models import Student, Class
    
    success_count = 0
    error_count = 0
    
    for data in enrollment_data:
        try:
            # Create or update student
            student, created = Student.objects.update_or_create(
                email=data['email'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'enrollment_date': timezone.now()
                }
            )
            
            # Enroll in classes
            for class_id in data.get('class_ids', []):
                class_obj = Class.objects.get(id=class_id)
                student.classes.add(class_obj)
            
            # Send welcome email
            send_student_welcome_email.delay(student.id)
            
            success_count += 1
            logger.info(f"Enrolled student: {student.email}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to enroll student: {str(e)}")
    
    return {'success': success_count, 'error': error_count}


@shared_task
def calculate_average_grade(class_obj):
    """Calculate average grade for a class"""
    # Implementation here
    return 85.5


@shared_task
def calculate_attendance_rate(class_obj, since_date):
    """Calculate attendance rate for a class"""
    # Implementation here
    return 0.95
```

## 8. Logistics App Tasks

```python
# apps/logistics/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from datetime import timedelta

logger = get_task_logger(__name__)

@shared_task
def track_shipments():
    """Track all active shipments"""
    from .models import Shipment
    
    active_shipments = Shipment.objects.filter(
        status__in=['in_transit', 'out_for_delivery']
    )
    
    for shipment in active_shipments:
        # Update shipment location (API call to tracking service)
        update_shipment_location.delay(shipment.id)
        
        # Check for delays
        check_shipment_delay.delay(shipment.id)
    
    logger.info(f"Tracking {active_shipments.count()} shipments")
    return active_shipments.count()


@shared_task
def update_shipment_location(shipment_id):
    """Update shipment location from tracking API"""
    from .models import Shipment
    
    try:
        shipment = Shipment.objects.get(id=shipment_id)
        
        # Call tracking API
        # location_data = tracking_api.get_location(shipment.tracking_number)
        
        # Update shipment
        # shipment.current_location = location_data['location']
        # shipment.status = location_data['status']
        # shipment.save()
        
        logger.info(f"Updated location for shipment {shipment_id}")
        return True
        
    except Shipment.DoesNotExist:
        logger.error(f"Shipment {shipment_id} not found")
        return False


@shared_task
def check_shipment_delay(shipment_id):
    """Check if shipment is delayed"""
    from .models import Shipment
    
    try:
        shipment = Shipment.objects.get(id=shipment_id)
        
        if shipment.estimated_delivery < timezone.now() and shipment.status != 'delivered':
            # Shipment is delayed
            shipment.status = 'delayed'
            shipment.save()
            
            # Notify customer
            notify_shipment_delay.delay(shipment_id)
            
            logger.warning(f"Shipment {shipment_id} is delayed")
            
        return True
        
    except Shipment.DoesNotExist:
        logger.error(f"Shipment {shipment_id} not found")
        return False


@shared_task(bind=True, base=EmailTask)
def notify_shipment_delay(self, shipment_id):
    """Notify customer about shipment delay"""
    from .models import Shipment
    
    try:
        shipment = Shipment.objects.select_related('order__user').get(id=shipment_id)
        user = shipment.order.user
        
        context = {
            'user': user,
            'shipment': shipment,
            'tracking_url': f"{settings.FRONTEND_URL}/track/{shipment.tracking_number}",
            'site_name': settings.SITE_NAME,
        }
        
        self.send_email(
            subject=f"Shipment Delay Notification - {settings.SITE_NAME}",
            template='shipment_delay',
            context=context,
            recipient_list=[user.email]
        )
        
        logger.info(f"Delay notification sent for shipment {shipment_id}")
        return True
        
    except Shipment.DoesNotExist:
        logger.error(f"Shipment {shipment_id} not found")
        return False


@shared_task
def optimize_delivery_routes():
    """Optimize delivery routes for carriers"""
    from .models import Carrier, DeliveryRoute
    
    active_carriers = Carrier.objects.filter(is_active=True)
    
    for carrier in active_carriers:
        # Get pending deliveries
        pending_deliveries = carrier.shipments.filter(
            status='out_for_delivery',
            delivery_date=timezone.now().date()
        )
        
        if pending_deliveries.exists():
            # Optimize route (use Google Maps API or similar)
            optimized_route = calculate_optimized_route(pending_deliveries)
            
            # Update routes
            DeliveryRoute.objects.update_or_create(
                carrier=carrier,
                date=timezone.now().date(),
                defaults={'route_data': optimized_route}
            )
            
            logger.info(f"Route optimized for carrier {carrier.id}")
    
    return True


@shared_task
def send_delivery_reminders():
    """Send delivery reminders to customers"""
    from .models import Shipment
    
    tomorrow = timezone.now().date() + timedelta(days=1)
    
    upcoming_deliveries = Shipment.objects.filter(
        estimated_delivery__date=tomorrow,
        status='in_transit'
    ).select_related('order__user')
    
    for shipment in upcoming_deliveries:
        send_delivery_reminder_email.delay(shipment.id)
    
    logger.info(f"Delivery reminders queued for {upcoming_deliveries.count()} shipments")
    return upcoming_deliveries.count()


@shared_task(bind=True, base=EmailTask)
def send_delivery_reminder_email(self, shipment_id):
    """Send delivery reminder email"""
    from .models import Shipment
    
    try:
        shipment = Shipment.objects.select_related('order__user').get(id=shipment_id)
        user = shipment.order.user
        
        context = {
            'user': user,
            'shipment': shipment,
            'tracking_url': f"{settings.FRONTEND_URL}/track/{shipment.tracking_number}",
            'delivery_date': shipment.estimated_delivery,
            'site_name': settings.SITE_NAME,
        }
        
        self.send_email(
            subject=f"Your Delivery is Coming Tomorrow - {settings.SITE_NAME}",
            template='delivery_reminder',
            context=context,
            recipient_list=[user.email]
        )
        
        logger.info(f"Delivery reminder sent for shipment {shipment_id}")
        return True
        
    except Shipment.DoesNotExist:
        logger.error(f"Shipment {shipment_id} not found")
        return False
```

## 9. Docker Compose for Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL database
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: your_project
      POSTGRES_USER: your_user
      POSTGRES_PASSWORD: your_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis for Celery broker
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # RabbitMQ (alternative to Redis)
  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - "5672:5672"  # AMQP
      - "15672:15672" # Management UI
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest

  # Celery worker
  celery_worker:
    build: .
    command: celery -A config worker -l info -Q accounts,commerce,school,logistics,emails
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://your_user:your_password@db:5432/your_project
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - db
      - redis
      - rabbitmq

  # Celery beat for periodic tasks
  celery_beat:
    build: .
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://your_user:your_password@db:5432/your_project
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - db
      - redis
      - rabbitmq

  # Flower for monitoring Celery
  flower:
    build: .
    command: celery -A config flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - celery_worker
      - celery_beat

volumes:
  postgres_data:
  redis_data:
```

## 10. Requirements

```txt
# requirements.txt
Django==4.2.0
celery==5.3.1
redis==5.0.0
django-celery-beat==2.5.0  # For periodic tasks
django-celery-results==2.5.0  # For storing task results
flower==2.0.0  # Monitoring
eventlet==0.33.3  # For Windows support
psycopg2-binary==2.9.6  # PostgreSQL
python-dotenv==1.0.0
```

## 11. Using Tasks in Views

```python
# apps/accounts/views.py (updated)
from .tasks import (
    send_welcome_email,
    send_password_reset_email,
    process_app_selection,
    send_login_alert
)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    # ... registration code ...
    
    # Queue welcome email (don't wait for it)
    send_welcome_email.delay(user.id)
    
    return Response(...)


@api_view(['POST'])
@permission_classes([AllowAny])
def select_applications(request):
    # ... selection code ...
    
    # Process app selection in background
    process_app_selection.delay(user.id, selected_apps)
    
    return Response(...)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    # ... reset code ...
    
    # Queue password reset email
    send_password_reset_email.delay(user.id, reset_token)
    
    return Response(...)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    # ... login code ...
    
    # Check if this is a new device and send alert
    if is_new_device(user, request):
        send_login_alert.delay(
            user.id,
            get_client_ip(request),
            request.META.get('HTTP_USER_AGENT', '')
        )
    
    return Response(...)
```

## 12. Monitoring with Django Admin

```python
# apps/accounts/admin.py (add Celery task monitoring)
from django_celery_results.models import TaskResult
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule

@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ['task_name', 'status', 'date_done', 'result']
    list_filter = ['status', 'task_name', 'date_done']
    search_fields = ['task_name', 'result']
    readonly_fields = ['date_done', 'traceback']


@admin.register(PeriodicTask)
class PeriodicTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'task', 'enabled', 'last_run_at', 'total_run_count']
    list_filter = ['enabled', 'task', 'last_run_at']
    search_fields = ['name', 'task']
    readonly_fields = ['last_run_at', 'total_run_count']
```

## 13. Running Celery

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery worker (development)
celery -A config worker -l info

# With specific queues
celery -A config worker -l info -Q accounts,commerce,emails

# Terminal 3: Start Celery beat for periodic tasks
celery -A config beat -l info

# Terminal 4: Start Flower monitoring
celery -A config flower --port=5555

# Production with multiple workers (using supervisord)
celery -A config worker -l info --concurrency=4 --max-tasks-per-child=200
```

This comprehensive Celery setup provides:

1. **Modular Task Organization**: Tasks organized by app
2. **Background Processing**: Email sending, data processing, report generation
3. **Periodic Tasks**: Automated cleanup, reports, reminders
4. **