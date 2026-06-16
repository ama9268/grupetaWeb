from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_approval_request_email(new_user):
    recipients = list(
        User.objects.filter(
            profile__role__in=['admin', 'moderator'],
            is_active=True,
        ).values_list('email', flat=True)
    )
    if not recipients:
        return

    subject = f'[GrupetaWeb] Nuevo registro pendiente de aprobación: {new_user.email}'
    ctx = {'new_user': new_user, 'site_url': settings.SITE_URL}
    html_body = render_to_string('accounts/emails/approval_request.html', ctx)
    text_body = render_to_string('accounts/emails/approval_request.txt', ctx)

    send_mail(
        subject=subject,
        message=text_body,
        html_message=html_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )


def send_account_approved_email(user):
    subject = '[GrupetaWeb] Tu cuenta ha sido aprobada'
    ctx = {'user': user, 'site_url': settings.SITE_URL}
    html_body = render_to_string('accounts/emails/account_approved.html', ctx)
    text_body = render_to_string('accounts/emails/account_approved.txt', ctx)

    send_mail(
        subject=subject,
        message=text_body,
        html_message=html_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
