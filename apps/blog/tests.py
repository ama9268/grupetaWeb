import pytest
from django.db import IntegrityError
from django.urls import reverse

from .models import Post, Comment, Like


@pytest.fixture
def post(db, approved_member):
    return Post.objects.create(
        title='Post de prueba',
        content='<p>Contenido de prueba</p>',
        author=approved_member,
    )


@pytest.fixture
def other_member(db):
    from django.contrib.auth.models import User
    user = User.objects.create_user(
        username='other@test.com',
        email='other@test.com',
        password='testpass123',
        is_active=True,
    )
    user.profile.role = 'member'
    user.profile.status = 'approved'
    user.profile.save()
    return user


@pytest.mark.django_db
def test_like_toggle_creates_then_deletes(member_client, approved_member, post):
    member_client.post(reverse('blog:toggle_like', args=[post.pk]))
    assert Like.objects.filter(post=post, user=approved_member).exists()

    member_client.post(reverse('blog:toggle_like', args=[post.pk]))
    assert not Like.objects.filter(post=post, user=approved_member).exists()


@pytest.mark.django_db
def test_double_like_prevented_by_unique_constraint(approved_member, post):
    Like.objects.create(post=post, user=approved_member)
    with pytest.raises(IntegrityError):
        Like.objects.create(post=post, user=approved_member)


@pytest.mark.django_db
def test_member_cannot_delete_others_comment(db, approved_member, other_member, post):
    from django.test import Client
    comment = Comment.objects.create(
        post=post,
        author=other_member,
        content='Comentario ajeno',
    )
    client = Client()
    client.login(username='member@test.com', password='testpass123')
    response = client.post(reverse('blog:delete_comment', args=[comment.pk]))

    assert response.status_code == 403
    assert Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
def test_moderator_can_delete_any_comment(approved_member, approved_moderator, moderator_client, post):
    comment = Comment.objects.create(
        post=post,
        author=approved_member,
        content='Comentario a borrar',
    )
    response = moderator_client.post(reverse('blog:delete_comment', args=[comment.pk]))

    assert response.status_code == 302
    assert not Comment.objects.filter(pk=comment.pk).exists()
