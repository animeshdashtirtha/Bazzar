from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from threading import Thread

def send_order_confirmation(to_email, order):
    if not to_email:
        return
    
    subject = f"Order #{order.id} Confirmation - Bazzar"

    # Render HTML template
    html_content = render_to_string(
        'orders/order_confirmation_email.html',
        {'user': order.user, 'order': order}
    )

    # Fallback plain text
    text_content = f"Thank you for your order #{order.id}! Total: ${order.total_price}"

    # Create email
    email = EmailMultiAlternatives(
        subject, text_content, settings.DEFAULT_FROM_EMAIL, [to_email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=True)


def send_email_async(func, *args, **kwargs):
    Thread(target=func, args=args, kwargs=kwargs).start()



def send_order_received(to_email, order):
    if not to_email:
        return
    
    subject = f"Order #{order.id} Received – Bazzar"

    html_content = render_to_string(
        'orders/order_received_email.html',
        {
            'user': order.user,
            'order': order,
        }
    )

    text_content = (
        f"Hi {order.user.username},\n\n"
        f"We’ve received your order #{order.id}.\n"
        f"Total: ${order.total_price}\n\n"
        f"We’ll notify you once it’s confirmed.\n\n"
        f"– Bazzar"
    )

    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=True)
