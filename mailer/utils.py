from django.conf import settings
from django.core.mail import send_mail


def send_notification_email(subject, message, recipient=None):
    """Invia una email di notifica usando il backend configurato.

    Se ``recipient`` non è specificato, usa ``DEFAULT_FROM_EMAIL`` come
    destinatario (come fa la view ``sendMail`` dell'app ``mailer``).
    Ritorna il numero di messaggi inviati.
    """
    recipient = recipient or [settings.DEFAULT_FROM_EMAIL]
    if isinstance(recipient, str):
        recipient = [recipient]
    return send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient)