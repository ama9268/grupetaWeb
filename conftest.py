import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.groups.constants import DEFAULT_GROUP_NAME, DEFAULT_GROUP_SLUG
from apps.groups.models import Group, Membership


@pytest.fixture
def default_group(db):
    group, _ = Group.objects.get_or_create(
        slug=DEFAULT_GROUP_SLUG, defaults={'name': DEFAULT_GROUP_NAME},
    )
    return group


@pytest.fixture
def approved_member(default_group):
    user = User.objects.create_user(
        username='member@test.com',
        email='member@test.com',
        password='testpass123',
        is_active=True,
    )
    Membership.objects.create(
        user=user, group=default_group, role=Membership.Role.MEMBER, status=Membership.Status.APPROVED,
    )
    return user


@pytest.fixture
def approved_moderator(default_group):
    user = User.objects.create_user(
        username='mod@test.com',
        email='mod@test.com',
        password='testpass123',
        is_active=True,
    )
    Membership.objects.create(
        user=user, group=default_group, role=Membership.Role.MODERATOR, status=Membership.Status.APPROVED,
    )
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
