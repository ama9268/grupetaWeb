import pytest
from django.db import IntegrityError
from django.urls import reverse

from .models import Post, Comment, Like


@pytest.fixture
def post(db, approved_member, default_group):
    return Post.objects.create(
        title='Post de prueba',
        content='<p>Contenido de prueba</p>',
        author=approved_member,
        group=default_group,
    )


@pytest.fixture
def other_member(default_group):
    from django.contrib.auth.models import User
    from apps.groups.models import Membership
    user = User.objects.create_user(
        username='other@test.com',
        email='other@test.com',
        password='testpass123',
        is_active=True,
    )
    Membership.objects.create(user=user, group=default_group, status=Membership.Status.APPROVED)
    return user


@pytest.mark.django_db
def test_post_content_is_sanitized_on_save(approved_member, default_group):
    post = Post.objects.create(
        title='XSS',
        content='<p>Hola</p><script>alert(1)</script><img src=x onerror="alert(2)">',
        author=approved_member,
        group=default_group,
    )
    post.refresh_from_db()
    assert '<script>' not in post.content
    assert 'onerror' not in post.content
    assert '<p>Hola</p>' in post.content


@pytest.mark.django_db
def test_post_sanitize_strips_javascript_href(approved_member, default_group):
    post = Post.objects.create(
        title='Enlace peligroso',
        content='<a href="javascript:alert(1)">click</a>',
        author=approved_member,
        group=default_group,
    )
    post.refresh_from_db()
    assert 'javascript:' not in post.content


@pytest.mark.django_db
def test_post_sanitize_keeps_safe_formatting(approved_member, default_group):
    post = Post.objects.create(
        title='Formato',
        content='<h2>Título</h2><p><strong>negrita</strong> y <a href="https://x.com">enlace</a></p>',
        author=approved_member,
        group=default_group,
    )
    post.refresh_from_db()
    assert '<strong>negrita</strong>' in post.content
    assert 'href="https://x.com"' in post.content


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
