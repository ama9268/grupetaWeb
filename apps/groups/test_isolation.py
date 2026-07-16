"""Tests de aislamiento entre grupetas: un usuario de la Grupeta A nunca debe
poder ver ni actuar sobre contenido de la Grupeta B a la que no pertenece.
Cubre el riesgo #1 identificado en el plan de multi-tenant (fuga de datos).
"""
import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Post
from apps.chat.models import ChatRoom
from apps.events.models import Event
from apps.media_gallery.models import MediaItem
from apps.routes.models import Route
from .models import Group, Membership


@pytest.fixture
def group_b(db):
    return Group.objects.create(name='Grupeta B', slug='grupeta-b')


@pytest.fixture
def member_b(group_b):
    user = User.objects.create_user(
        username='member-b', email='member-b@test.com', password='testpass123', is_active=True,
    )
    Membership.objects.create(user=user, group=group_b, status=Membership.Status.APPROVED)
    return user


@pytest.fixture
def moderator_b(group_b):
    user = User.objects.create_user(
        username='mod-b', email='mod-b@test.com', password='testpass123', is_active=True,
    )
    Membership.objects.create(
        user=user, group=group_b, role=Membership.Role.MODERATOR, status=Membership.Status.APPROVED,
    )
    return user


@pytest.fixture
def client_b(member_b):
    client = Client()
    client.login(username='member-b', password='testpass123')
    return client


@pytest.fixture
def mod_client_b(moderator_b):
    client = Client()
    client.login(username='mod-b', password='testpass123')
    return client


@pytest.fixture
def event_a(default_group, approved_moderator):
    return Event.objects.create(
        title='Evento de A', start_at=timezone.now() + timedelta(days=3),
        created_by=approved_moderator, group=default_group,
    )


@pytest.mark.django_db
def test_member_of_b_cannot_view_event_of_a(client_b, event_a):
    response = client_b.get(reverse('events:detail', args=[event_a.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_moderator_of_b_cannot_accept_event_of_a(mod_client_b, event_a):
    response = mod_client_b.post(reverse('events:accept', args=[event_a.pk]))
    assert response.status_code == 403
    event_a.refresh_from_db()
    assert event_a.state == Event.State.PENDIENTE


@pytest.mark.django_db
def test_member_of_a_does_not_see_event_of_b_in_list(member_client, group_b, approved_moderator, default_group):
    Event.objects.create(
        title='Evento exclusivo de B', start_at=timezone.now() + timedelta(days=3),
        created_by=approved_moderator, group=group_b,
    )
    response = member_client.get(reverse('events:list'))
    assert b'Evento exclusivo de B' not in response.content


@pytest.mark.django_db
def test_member_of_b_cannot_view_chat_room_of_a(client_b, default_group):
    room = ChatRoom.objects.get(slug='general', group=default_group)
    response = client_b.get(reverse('chat:room_detail', args=[room.slug]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_member_of_b_cannot_view_post_of_a(client_b, default_group, approved_member):
    post = Post.objects.create(
        title='Post de A', content='<p>hola</p>', author=approved_member, group=default_group,
    )
    response = client_b.get(reverse('blog:detail', args=[post.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_member_of_b_cannot_like_post_of_a(client_b, default_group, approved_member):
    post = Post.objects.create(
        title='Post de A', content='<p>hola</p>', author=approved_member, group=default_group,
    )
    response = client_b.post(reverse('blog:toggle_like', args=[post.pk]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_member_directory_does_not_leak_across_groups(member_client, member_b, default_group):
    response = member_client.get(reverse('members:list'))
    members = response.context['members']
    assert member_b.profile not in list(members)


@pytest.mark.django_db
def test_gallery_does_not_leak_across_groups(member_client, group_b, approved_member, default_group):
    MediaItem.objects.create(
        group=group_b, uploaded_by=approved_member, media_type='image',
        cloudinary_public_id='x', cloudinary_url='https://cdn/x.webp', title='Foto de B',
    )
    response = member_client.get(reverse('media_gallery:list'))
    assert b'Foto de B' not in response.content


@pytest.mark.django_db
def test_member_of_b_cannot_view_route_of_a(client_b, default_group, approved_member):
    route = Route.objects.create(group=default_group, title='Ruta de A', author=approved_member)
    response = client_b.get(reverse('routes:detail', args=[route.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_member_of_a_does_not_see_route_of_b_in_list(member_client, group_b, approved_member, default_group):
    Route.objects.create(group=group_b, title='Ruta exclusiva de B', author=approved_member)
    response = member_client.get(reverse('routes:list'))
    assert b'Ruta exclusiva de B' not in response.content


@pytest.mark.django_db
def test_moderator_of_b_cannot_create_route_in_group_of_a(mod_client_b, default_group):
    response = mod_client_b.post(reverse('routes:create'), {
        'group': default_group.pk, 'title': 'Ruta colada',
    })
    assert response.status_code == 200
    assert not Route.objects.filter(title='Ruta colada').exists()
