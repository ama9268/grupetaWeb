import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client
from django.urls import reverse

from .models import UserProfile


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username='admin@test.com',
        email='admin@test.com',
        password='testpass123',
        is_active=True,
    )
    user.profile.role = 'admin'
    user.profile.status = 'approved'
    user.profile.save()
    return user


@pytest.fixture
def client_admin(admin_user):
    client = Client()
    client.login(username='admin@test.com', password='testpass123')
    return client


@pytest.mark.django_db
def test_signup_creates_inactive_user_pending_approval():
    client = Client()
    response = client.post(reverse('account_signup'), {
        'email': 'nuevo@test.com',
        'username': 'nuevo',
        'password1': 'SuperSecure123!',
        'password2': 'SuperSecure123!',
    })
    user = User.objects.filter(email='nuevo@test.com').first()
    assert user is not None
    assert user.username == 'nuevo'
    assert user.is_active is False
    assert user.profile.status == 'pending'


@pytest.mark.django_db
def test_signup_sends_email_to_admins(admin_user, settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    client = Client()
    client.post(reverse('account_signup'), {
        'email': 'nuevo@test.com',
        'username': 'nuevo',
        'password1': 'SuperSecure123!',
        'password2': 'SuperSecure123!',
    })
    assert len(mail.outbox) == 1
    assert admin_user.email in mail.outbox[0].recipients()


@pytest.mark.django_db
def test_approve_user_activates_account(admin_user, settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    pending = User.objects.create_user(
        username='pending@test.com',
        email='pending@test.com',
        password='testpass123',
        is_active=False,
    )
    pending.profile.status = 'pending'
    pending.profile.save()

    client = Client()
    client.login(username='admin@test.com', password='testpass123')
    client.post(reverse('accounts:approve_user', args=[pending.pk]))

    pending.refresh_from_db()
    assert pending.is_active is True
    assert pending.profile.status == 'approved'
    assert any(pending.email in m.to for m in mail.outbox)


@pytest.mark.django_db
def test_moderator_cannot_promote_member_to_admin(moderator_client, approved_member):
    resp = moderator_client.post(
        reverse('accounts:change_role', args=[approved_member.pk]), {'role': 'admin'}
    )
    assert resp.status_code == 403
    approved_member.profile.refresh_from_db()
    assert approved_member.profile.role == 'member'


@pytest.mark.django_db
def test_moderator_cannot_modify_an_admin(moderator_client, admin_user):
    resp = moderator_client.post(
        reverse('accounts:change_role', args=[admin_user.pk]), {'role': 'member'}
    )
    assert resp.status_code == 403
    admin_user.profile.refresh_from_db()
    assert admin_user.profile.role == 'admin'


@pytest.mark.django_db
def test_moderator_can_set_moderator_role(moderator_client, approved_member):
    moderator_client.post(
        reverse('accounts:change_role', args=[approved_member.pk]), {'role': 'moderator'}
    )
    approved_member.profile.refresh_from_db()
    assert approved_member.profile.role == 'moderator'


@pytest.mark.django_db
def test_admin_can_promote_to_admin(client_admin, approved_member):
    client_admin.post(
        reverse('accounts:change_role', args=[approved_member.pk]), {'role': 'admin'}
    )
    approved_member.profile.refresh_from_db()
    assert approved_member.profile.role == 'admin'


@pytest.mark.django_db
def test_cannot_demote_last_admin(client_admin, admin_user):
    # admin_user es el único admin activo: no puede degradarse a sí mismo.
    client_admin.post(
        reverse('accounts:change_role', args=[admin_user.pk]), {'role': 'member'}
    )
    admin_user.profile.refresh_from_db()
    assert admin_user.profile.role == 'admin'


@pytest.mark.django_db
def test_can_demote_admin_when_another_admin_exists(client_admin, admin_user):
    other = User.objects.create_user(
        username='otro-admin', email='otro-admin@test.com',
        password='testpass123', is_active=True,
    )
    other.profile.role = 'admin'
    other.profile.status = 'approved'
    other.profile.save()

    client_admin.post(
        reverse('accounts:change_role', args=[other.pk]), {'role': 'member'}
    )
    other.profile.refresh_from_db()
    assert other.profile.role == 'member'


@pytest.mark.django_db
def test_manage_users_renders_for_moderator(moderator_client, admin_user):
    # El panel renderiza para un moderador; un admin de la lista se muestra en solo lectura.
    resp = moderator_client.get(reverse('accounts:manage_users'))
    assert resp.status_code == 200
    assert b'Admin' in resp.content


@pytest.mark.django_db
def test_member_cannot_access_manage_users(admin_user):
    member = User.objects.create_user(
        username='miembro@test.com',
        email='miembro@test.com',
        password='testpass123',
        is_active=True,
    )
    member.profile.role = 'member'
    member.profile.status = 'approved'
    member.profile.save()

    client = Client()
    client.login(username='miembro@test.com', password='testpass123')
    response = client.get(reverse('accounts:manage_users'))
    assert response.status_code == 403
