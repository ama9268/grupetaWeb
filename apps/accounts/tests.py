import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client
from django.urls import reverse

from apps.groups.models import Group, Membership


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username='admin@test.com',
        email='admin@test.com',
        password='testpass123',
        is_active=True,
    )
    user.profile.is_admin = True
    user.profile.save()
    return user


@pytest.fixture
def client_admin(admin_user):
    client = Client()
    client.login(username='admin@test.com', password='testpass123')
    return client


@pytest.mark.django_db
def test_signup_creates_inactive_user_pending_approval(default_group):
    client = Client()
    response = client.post(reverse('account_signup'), {
        'email': 'nuevo@test.com',
        'username': 'nuevo',
        'password1': 'SuperSecure123!',
        'password2': 'SuperSecure123!',
        'group': default_group.pk,
    })
    user = User.objects.filter(email='nuevo@test.com').first()
    assert user is not None
    assert user.username == 'nuevo'
    assert user.is_active is False
    assert not user.profile.is_approved


@pytest.mark.django_db
def test_signup_creates_pending_membership_in_chosen_group(default_group):
    client = Client()
    client.post(reverse('account_signup'), {
        'email': 'nuevo3@test.com',
        'username': 'nuevo3',
        'password1': 'SuperSecure123!',
        'password2': 'SuperSecure123!',
        'group': default_group.pk,
    })
    user = User.objects.get(email='nuevo3@test.com')
    membership = Membership.objects.get(user=user, group=default_group)
    assert membership.status == Membership.Status.PENDING
    assert membership.role == Membership.Role.MEMBER


@pytest.mark.django_db
def test_pending_membership_notifies_group_moderators_and_admins(
    admin_user, approved_moderator, default_group, settings
):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    other_user = User.objects.create_user(
        username='nuevo', email='nuevo@test.com', password='testpass123', is_active=False,
    )
    Membership.objects.create(user=other_user, group=default_group, status=Membership.Status.PENDING)

    assert len(mail.outbox) == 1
    recipients = mail.outbox[0].recipients()
    assert admin_user.email in recipients
    assert approved_moderator.email in recipients


@pytest.mark.django_db
def test_pending_membership_does_not_notify_moderators_of_other_group(
    admin_user, approved_moderator, settings
):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    other_group = Group.objects.create(name='Otra grupeta', slug='otra-grupeta')
    other_user = User.objects.create_user(
        username='nuevo2', email='nuevo2@test.com', password='testpass123', is_active=False,
    )
    Membership.objects.create(user=other_user, group=other_group, status=Membership.Status.PENDING)

    recipients = mail.outbox[0].recipients()
    # approved_moderator modera default_group, no other_group.
    assert approved_moderator.email not in recipients
    # El Admin global se entera de las solicitudes de cualquier grupeta.
    assert admin_user.email in recipients


@pytest.mark.django_db
def test_approve_user_activates_account(admin_user, default_group, settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    pending_user = User.objects.create_user(
        username='pending@test.com',
        email='pending@test.com',
        password='testpass123',
        is_active=False,
    )
    membership = Membership.objects.create(
        user=pending_user, group=default_group, status=Membership.Status.PENDING,
    )

    client = Client()
    client.login(username='admin@test.com', password='testpass123')
    client.post(reverse('accounts:approve_user', args=[membership.pk]))

    pending_user.refresh_from_db()
    membership.refresh_from_db()
    assert pending_user.is_active is True
    assert membership.status == Membership.Status.APPROVED
    assert any(pending_user.email in m.to for m in mail.outbox)


@pytest.mark.django_db
def test_reject_user_does_not_activate_account(admin_user, default_group):
    pending_user = User.objects.create_user(
        username='pending2@test.com',
        email='pending2@test.com',
        password='testpass123',
        is_active=False,
    )
    membership = Membership.objects.create(
        user=pending_user, group=default_group, status=Membership.Status.PENDING,
    )

    client = Client()
    client.login(username='admin@test.com', password='testpass123')
    client.post(reverse('accounts:reject_user', args=[membership.pk]))

    pending_user.refresh_from_db()
    membership.refresh_from_db()
    assert pending_user.is_active is False
    assert membership.status == Membership.Status.REJECTED


@pytest.mark.django_db
def test_change_role_ignores_admin_value(moderator_client, approved_member, default_group):
    membership = Membership.objects.get(user=approved_member, group=default_group)
    resp = moderator_client.post(reverse('accounts:change_role', args=[membership.pk]), {'role': 'admin'})
    assert resp.status_code == 302
    membership.refresh_from_db()
    assert membership.role == Membership.Role.MEMBER


@pytest.mark.django_db
def test_moderator_can_promote_member_to_moderator(moderator_client, approved_member, default_group):
    membership = Membership.objects.get(user=approved_member, group=default_group)
    moderator_client.post(reverse('accounts:change_role', args=[membership.pk]), {'role': 'moderator'})
    membership.refresh_from_db()
    assert membership.role == Membership.Role.MODERATOR


@pytest.mark.django_db
def test_cannot_demote_last_moderator_of_group(moderator_client, approved_moderator, default_group):
    membership = Membership.objects.get(user=approved_moderator, group=default_group)
    moderator_client.post(reverse('accounts:change_role', args=[membership.pk]), {'role': 'member'})
    membership.refresh_from_db()
    # No se pudo degradar: approved_moderator es el único moderador de la grupeta.
    assert membership.role == Membership.Role.MODERATOR


@pytest.mark.django_db
def test_can_demote_moderator_when_another_exists(moderator_client, approved_moderator, default_group):
    other_mod = User.objects.create_user(
        username='otro-mod', email='otro-mod@test.com', password='testpass123', is_active=True,
    )
    Membership.objects.create(
        user=other_mod, group=default_group,
        role=Membership.Role.MODERATOR, status=Membership.Status.APPROVED,
    )

    membership = Membership.objects.get(user=approved_moderator, group=default_group)
    moderator_client.post(reverse('accounts:change_role', args=[membership.pk]), {'role': 'member'})
    membership.refresh_from_db()
    assert membership.role == Membership.Role.MEMBER


@pytest.mark.django_db
def test_manage_users_renders_for_moderator(moderator_client, admin_user):
    resp = moderator_client.get(reverse('accounts:manage_users'))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_member_cannot_access_manage_users(member_client):
    response = member_client.get(reverse('accounts:manage_users'))
    assert response.status_code == 403
