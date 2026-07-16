import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse


def _profile_post(username='member', email='member@test.com', **extra):
    data = {
        'username': username,
        'first_name': '',
        'last_name': '',
        'email': email,
        'bio': '',
        'bikes': '',
    }
    data.update(extra)
    return data


@pytest.mark.django_db
def test_member_edits_own_profile(member_client, approved_member):
    resp = member_client.post(
        reverse('members:profile_edit'),
        _profile_post(username='rodador', first_name='Ana', bio='Hola'),
    )
    assert resp.status_code == 302
    approved_member.refresh_from_db()
    assert approved_member.username == 'rodador'
    assert approved_member.first_name == 'Ana'
    assert approved_member.profile.bio == 'Hola'
    # rol/estado de membership intactos
    assert not approved_member.profile.is_moderator
    assert approved_member.profile.is_approved


@pytest.mark.django_db
def test_role_and_status_not_editable_from_profile_form(member_client, approved_member):
    # POST manipulado intentando escalar rol/estado: debe ignorarse.
    member_client.post(
        reverse('members:profile_edit'),
        _profile_post(role='admin', status='approved'),
    )
    approved_member.refresh_from_db()
    assert not approved_member.profile.is_admin
    assert not approved_member.profile.is_moderator


@pytest.mark.django_db
def test_email_change_syncs_allauth(member_client, approved_member):
    member_client.post(
        reverse('members:profile_edit'),
        _profile_post(email='nuevo@test.com'),
    )
    approved_member.refresh_from_db()
    assert approved_member.email == 'nuevo@test.com'
    ea = EmailAddress.objects.get(user=approved_member, email='nuevo@test.com')
    assert ea.primary is True
    assert ea.verified is True


@pytest.mark.django_db
def test_username_uniqueness_case_insensitive(member_client, approved_member):
    User.objects.create_user(username='taken', email='taken@test.com')
    resp = member_client.post(
        reverse('members:profile_edit'),
        _profile_post(username='Taken'),
    )
    assert resp.status_code == 200  # re-render con error
    approved_member.refresh_from_db()
    assert approved_member.username == 'member@test.com'  # sin cambios


@pytest.mark.django_db
def test_invalid_username_format_rejected(member_client, approved_member):
    resp = member_client.post(
        reverse('members:profile_edit'),
        _profile_post(username='con espacios!'),
    )
    assert resp.status_code == 200
    approved_member.refresh_from_db()
    assert approved_member.username == 'member@test.com'


@pytest.mark.django_db
def test_moderator_can_edit_other_member(moderator_client, approved_member):
    resp = moderator_client.post(
        reverse('members:profile_edit_member', args=[approved_member.profile.pk]),
        _profile_post(username='editado'),
    )
    assert resp.status_code == 302
    approved_member.refresh_from_db()
    assert approved_member.username == 'editado'


@pytest.mark.django_db
def test_member_cannot_edit_other_member(member_client, approved_moderator):
    resp = member_client.post(
        reverse('members:profile_edit_member', args=[approved_moderator.profile.pk]),
        _profile_post(username='hackeo'),
    )
    assert resp.status_code == 403
    approved_moderator.refresh_from_db()
    assert approved_moderator.username == 'mod@test.com'
