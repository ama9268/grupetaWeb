import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from .constants import DEFAULT_GROUP_SLUG
from .models import Group, Membership
from .utils import resolve_active_group


@pytest.fixture
def group(db):
    return Group.objects.create(name='Peña Ciclista Test', slug='pena-ciclista-test')


@pytest.fixture
def user(db):
    return User.objects.create_user(username='ciclista', email='ciclista@test.com', password='testpass123')


@pytest.mark.django_db
def test_default_group_created_by_migration():
    assert Group.objects.filter(slug=DEFAULT_GROUP_SLUG, is_active=True).exists()


@pytest.mark.django_db
def test_group_queryset_active_filters_inactive_groups(group):
    inactive = Group.objects.create(name='Grupeta Inactiva', slug='grupeta-inactiva', is_active=False)
    active_slugs = set(Group.objects.active().values_list('slug', flat=True))
    assert group.slug in active_slugs
    assert inactive.slug not in active_slugs


@pytest.mark.django_db
def test_membership_defaults_to_pending_member(group, user):
    membership = Membership.objects.create(user=user, group=group)
    assert membership.role == Membership.Role.MEMBER
    assert membership.status == Membership.Status.PENDING


@pytest.mark.django_db
def test_membership_unique_per_user_and_group(group, user):
    Membership.objects.create(user=user, group=group)
    with pytest.raises(IntegrityError):
        Membership.objects.create(user=user, group=group)


# --- Grupeta activa (sesión, selector de navegación) ---

@pytest.mark.django_db
def test_default_active_group_is_oldest_approved_membership(approved_member, default_group, group):
    Membership.objects.create(user=approved_member, group=group, status=Membership.Status.APPROVED)
    factory_request = type('Req', (), {'session': {}})()
    resolved = resolve_active_group(factory_request, approved_member.profile)
    assert resolved == default_group  # la membership de conftest es anterior a `group`


@pytest.mark.django_db
def test_set_active_group_updates_session_and_redirects(member_client, approved_member, group):
    Membership.objects.create(user=approved_member, group=group, status=Membership.Status.APPROVED)
    resp = member_client.post(
        reverse('groups:set_active'), {'slug': group.slug, 'next': '/eventos/'},
    )
    assert resp.status_code == 302
    assert resp.url == '/eventos/'
    assert member_client.session['active_group_slug'] == group.slug


@pytest.mark.django_db
def test_set_active_group_rejects_group_user_is_not_member_of(member_client, group):
    # approved_member (fixture) no pertenece a `group`.
    resp = member_client.post(reverse('groups:set_active'), {'slug': group.slug})
    assert resp.status_code == 404


@pytest.mark.django_db
def test_active_group_context_processor_exposes_current_group(member_client, default_group):
    resp = member_client.get(reverse('members:list'))
    assert resp.context['nav_active_group'] == default_group


# --- Autoservicio: crear grupeta / unirse a una adicional ---

@pytest.mark.django_db
def test_group_create_makes_creator_approved_moderator(member_client, approved_member):
    resp = member_client.post(
        reverse('groups:create'), {'name': 'Nueva Grupeta', 'description': 'Una grupeta nueva'},
    )
    assert resp.status_code == 302
    new_group = Group.objects.get(name='Nueva Grupeta')
    assert new_group.created_by == approved_member
    membership = Membership.objects.get(user=approved_member, group=new_group)
    assert membership.role == Membership.Role.MODERATOR
    assert membership.status == Membership.Status.APPROVED


@pytest.mark.django_db
def test_group_create_requires_approved_member():
    client = Client()
    resp = client.post(reverse('groups:create'), {'name': 'X'})
    assert resp.status_code == 302  # redirige a login


@pytest.mark.django_db
def test_request_join_group_creates_pending_membership(member_client, approved_member, group):
    resp = member_client.post(reverse('groups:request_join', args=[group.slug]))
    assert resp.status_code == 302
    membership = Membership.objects.get(user=approved_member, group=group)
    assert membership.status == Membership.Status.PENDING
    assert membership.role == Membership.Role.MEMBER


@pytest.mark.django_db
def test_request_join_group_reopens_rejected_membership(member_client, approved_member, group, settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    Membership.objects.create(user=approved_member, group=group, status=Membership.Status.REJECTED)
    member_client.post(reverse('groups:request_join', args=[group.slug]))
    membership = Membership.objects.get(user=approved_member, group=group)
    assert membership.status == Membership.Status.PENDING


@pytest.mark.django_db
def test_group_list_shows_membership_status(member_client, approved_member, default_group, group):
    resp = member_client.get(reverse('groups:list'))
    rows = {row['group'].pk: row['membership'] for row in resp.context['groups']}
    assert rows[default_group.pk].status == Membership.Status.APPROVED
    assert rows[group.pk] is None
