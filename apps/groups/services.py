from django.utils import timezone

from .models import Membership


def approve_membership(membership, decided_by):
    """Aprueba una solicitud de pertenencia a una grupeta.

    Si es la primera Membership aprobada del usuario, activa la cuenta (acceso
    a la plataforma) y envía el email de bienvenida; si el usuario ya estaba
    activo (aprobado en otra grupeta), envía un aviso más ligero de admisión.
    """
    is_first_approval = not membership.user.is_active

    membership.status = Membership.Status.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = decided_by
    membership.save(update_fields=['status', 'decided_at', 'decided_by'])

    from apps.accounts.emails import send_account_approved_email, send_membership_approved_email
    if is_first_approval:
        user = membership.user
        user.is_active = True
        user.save(update_fields=['is_active'])
        send_account_approved_email(user)
    else:
        send_membership_approved_email(membership.user, membership.group)

    return membership


def reject_membership(membership, decided_by):
    membership.status = Membership.Status.REJECTED
    membership.decided_at = timezone.now()
    membership.decided_by = decided_by
    membership.save(update_fields=['status', 'decided_at', 'decided_by'])
    return membership
