from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_welcome_email_task(user_email):
    # get app name from settings / requests or hardcode it
    app_registered = "commerce"
    subject = "Welcome to E-commerce Nexus"
    message = "celery ! Thank you for registering at app_registered."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user_email]

    # why return ?: for status in the terminal! (0 | 1)
    return send_mail(subject, message, from_email, recipient_list)


@shared_task
def send_order_confirmation_email_task(user_email, order_id):
    subject = "Order Confirmation"
    message = f"Thank you for your order! Your order ID is {order_id}. We will notify you once it is shipped."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user_email]

    # return: for status in the terminal! (0 | 1)
    return send_mail(subject, message, from_email, recipient_list)
