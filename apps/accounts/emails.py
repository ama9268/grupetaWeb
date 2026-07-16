from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_approval_request_email(membership):
    """Avisa de una solicitud de alta pendiente a los moderadores de ESA grupeta
    concreta (`membership.group`) y a todos los Admin globales."""
    from apps.groups.models import Membership

    recipients = set(
        User.objects.filter(
            memberships__group=membership.group,
            memberships__role=Membership.Role.MODERATOR,
            memberships__status=Membership.Status.APPROVED,
            is_active=True,
        ).values_list('email', flat=True)
    )
    recipients |= set(
        User.objects.filter(profile__is_admin=True, is_active=True).values_list('email', flat=True)
    )
    recipients.discard('')
    if not recipients:
        return

    subject = f'[GrupetaWeb] Nuevo registro pendiente en {membership.group.name}: {membership.user.email}'
    ctx = {'new_user': membership.user, 'group': membership.group, 'site_url': settings.SITE_URL}
    html_body = render_to_string('accounts/emails/approval_request.html', ctx)
    text_body = render_to_string('accounts/emails/approval_request.txt', ctx)

    send_mail(
        subject=subject,
        message=text_body,
        html_message=html_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=list(recipients),
        fail_silently=False,
    )


def send_account_approved_email(user):
    """Bienvenida a la plataforma: se envía en la PRIMERA aprobación del usuario."""
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


def send_membership_approved_email(user, group):
    """Admisión en una grupeta ADICIONAL: el usuario ya tenía acceso a la plataforma."""
    subject = f'[GrupetaWeb] Te han admitido en {group.name}'
    ctx = {'user': user, 'group': group, 'site_url': settings.SITE_URL}
    html_body = render_to_string('accounts/emails/membership_approved.html', ctx)
    text_body = render_to_string('accounts/emails/membership_approved.txt', ctx)

    send_mail(
        subject=subject,
        message=text_body,
        html_message=html_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
