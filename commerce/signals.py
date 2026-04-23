"""
Docstring for signals
this file contains all the signals for the commerce application
1. sending welcome email for first time users
2. order_completed: signal sent when an order is completed

"""

from django.dispatch import receiver
from django.db.models.signals import post_save
from commerce.models  import User
from django.core.mail import send_mail
import logging
from django.utils.log import DEFAULT_LOGGING

logger = logging.getLogger("django")

@receiver(post_save, sender=User)
def send_wellcome_email(sender, instance, created, **kwargs):
    # sends welcome message to new user
    if created:
        logger.info(f"Dear {instance}, your account with email {instance.email} has been created...")

        # print(f"hello, {instance.email}, {created} {DEFAULT_LOGGING}")
        # subject=f"Welcome to {settings.SITE_NAME}!"
        # from_email=settings.DEFAULT_FROM_EMAIL
        
        send_mail(
            subject="Welcome to Commerce",
            message=f"Dear {instance.first_name} your account has been created...",
            from_email="admin@example.com",
            recipient_list=[instance.email],
            fail_silently=True
        )

        if send_mail:
            print("mail sent !")
        else:
            print("not sent ! see debug...")

def show_logs():
    logger.info("This is an info log")
    logger.debug("This is a debug log")
    logger.warning("This is a warning log")
    logger.error("This is an error log")
