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
        'password1': 'SuperSecure123!',
        'password2': 'SuperSecure123!',
    })
    user = User.objects.filter(email='nuevo@test.com').first()
    assert user is not None
    assert user.is_active is False
    assert user.profile.status == 'pending'


@pytest.mark.django_db
def test_signup_sends_email_to_admins(admin_user, settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    client = Client()
    client.post(reverse('account_signup'), {
        'email': 'nuevo@test.com',
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
