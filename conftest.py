import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.fixture
def approved_member(db):
    user = User.objects.create_user(
        username='member@test.com',
        email='member@test.com',
        password='testpass123',
        is_active=True,
    )
    user.profile.role = 'member'
    user.profile.status = 'approved'
    user.profile.save()
    return user


@pytest.fixture
def approved_moderator(db):
    user = User.objects.create_user(
        username='mod@test.com',
        email='mod@test.com',
        password='testpass123',
        is_active=True,
    )
    user.profile.role = 'moderator'
    user.profile.status = 'approved'
    user.profile.save()
    return user


@pytest.fixture
def member_client(approved_member):
    client = Client()
    client.login(username='member@test.com', password='testpass123')
    return client


@pytest.fixture
def moderator_client(approved_moderator):
    client = Client()
    client.login(username='mod@test.com', password='testpass123')
    return client
