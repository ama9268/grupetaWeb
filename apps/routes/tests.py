import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.groups.models import Group, Membership

from .models import Route
from .strava import decrypt_token, encrypt_token

MINIMAL_GPX = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1" creator="test">
  <trk>
    <trkseg>
      <trkpt lat="40.4168" lon="-3.7038"><ele>650</ele><time>2024-06-01T09:00:00Z</time></trkpt>
      <trkpt lat="40.4200" lon="-3.7000"><ele>680</ele><time>2024-06-01T09:05:00Z</time></trkpt>
      <trkpt lat="40.4250" lon="-3.6950"><ele>670</ele><time>2024-06-01T09:12:00Z</time></trkpt>
    </trkseg>
  </trk>
</gpx>"""


def _gpx_file(name='ruta.gpx'):
    return SimpleUploadedFile(name, MINIMAL_GPX, content_type='application/gpx+xml')


@pytest.mark.django_db
def test_gpx_upload_extracts_stats_and_scopes_to_group(default_group, approved_moderator, moderator_client):
    response = moderator_client.post(reverse('routes:create'), {
        'group': default_group.pk,
        'title': 'Ruta de prueba',
        'description': 'Test',
        'gpx_file': _gpx_file(),
    })

    assert response.status_code == 302
    route = Route.objects.get(title='Ruta de prueba')
    assert route.group == default_group
    assert route.distance_km is not None and route.distance_km > 0
    assert route.elevation_gain_m is not None
    assert route.start_point is not None
    assert route.track_geom is not None

    approved_moderator.profile.refresh_from_db()
    assert approved_moderator.profile.total_routes == 1
    assert approved_moderator.profile.total_km > 0


@pytest.mark.django_db
def test_member_cannot_create_route(member_client, default_group):
    response = member_client.post(reverse('routes:create'), {
        'group': default_group.pk,
        'title': 'Ruta prohibida',
        'gpx_file': _gpx_file(),
    })
    assert response.status_code == 403
    assert not Route.objects.filter(title='Ruta prohibida').exists()


@pytest.mark.django_db
def test_moderator_cannot_create_route_in_a_group_they_do_not_moderate(moderator_client):
    other_group = Group.objects.create(name='Otra grupeta', slug='otra-grupeta')
    response = moderator_client.post(reverse('routes:create'), {
        'group': other_group.pk,
        'title': 'Ruta ajena',
        'gpx_file': _gpx_file(),
    })
    assert response.status_code == 200  # formulario inválido: grupeta fuera de su queryset
    assert not Route.objects.filter(title='Ruta ajena').exists()


@pytest.mark.django_db
def test_route_list_only_shows_active_group(default_group, approved_member, member_client):
    other_group = Group.objects.create(name='Otra grupeta', slug='otra-grupeta')
    author = approved_member
    Route.objects.create(group=default_group, title='Ruta de mi grupeta', author=author)
    Route.objects.create(group=other_group, title='Ruta de otra grupeta', author=author)

    response = member_client.get(reverse('routes:list'))
    assert b'Ruta de mi grupeta' in response.content
    assert b'Ruta de otra grupeta' not in response.content


@pytest.mark.django_db
def test_route_detail_serializes_track_as_json_script(default_group, approved_member, member_client):
    route = Route.objects.create(
        group=default_group, title='Ruta con trazado', author=approved_member,
        track_geojson=[[40.4168, -3.7038], [40.42, -3.70]],
        elevation_profile=[{'d': 0.0, 'e': 650}, {'d': 0.5, 'e': 680}],
    )
    response = member_client.get(reverse('routes:detail', args=[route.pk]))
    assert response.status_code == 200
    # Los datos van en islas <script type="application/json"> (json_script), no inline con |safe.
    assert b'id="route-track-data"' in response.content
    assert b'application/json' in response.content
    assert b'40.4168' in response.content


@pytest.mark.django_db
def test_route_detail_handles_missing_track(default_group, approved_member, member_client):
    route = Route.objects.create(group=default_group, title='Ruta sin trazado', author=approved_member)
    response = member_client.get(reverse('routes:detail', args=[route.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_gpx_upload_rejects_invalid_file(default_group, moderator_client):
    fake_gpx = SimpleUploadedFile('trampa.gpx', b'esto no es un gpx', content_type='application/gpx+xml')
    response = moderator_client.post(reverse('routes:create'), {
        'group': default_group.pk,
        'title': 'Ruta falsa',
        'description': '',
        'gpx_file': fake_gpx,
    })

    assert response.status_code == 200
    assert not Route.objects.filter(title='Ruta falsa').exists()


@pytest.mark.django_db
def test_duplicate_route_in_same_group_shows_warning_but_still_creates(default_group, moderator_client):
    moderator_client.post(reverse('routes:create'), {
        'group': default_group.pk, 'title': 'Ruta original', 'gpx_file': _gpx_file('r1.gpx'),
    })
    response = moderator_client.post(reverse('routes:create'), {
        'group': default_group.pk, 'title': 'Ruta repetida', 'gpx_file': _gpx_file('r2.gpx'),
    }, follow=True)

    assert Route.objects.filter(title='Ruta repetida').exists()
    warnings = [str(m) for m in response.context['messages']]
    assert any('ya existiera' in m for m in warnings)


@pytest.mark.django_db
def test_duplicate_check_does_not_cross_groups(default_group, approved_moderator, moderator_client):
    other_group = Group.objects.create(name='Otra grupeta', slug='otra-grupeta')
    Membership.objects.create(
        user=approved_moderator, group=other_group,
        role=Membership.Role.MODERATOR, status=Membership.Status.APPROVED,
    )

    moderator_client.post(reverse('routes:create'), {
        'group': default_group.pk, 'title': 'Ruta original', 'gpx_file': _gpx_file('r1.gpx'),
    })
    response = moderator_client.post(reverse('routes:create'), {
        'group': other_group.pk, 'title': 'Ruta en otra grupeta', 'gpx_file': _gpx_file('r2.gpx'),
    }, follow=True)

    assert Route.objects.filter(title='Ruta en otra grupeta').exists()
    warnings = [str(m) for m in response.context['messages']]
    assert not any('ya existiera' in m for m in warnings)


@pytest.mark.django_db
def test_strava_connect_requires_moderator(member_client):
    response = member_client.get(reverse('routes:strava_connect'))
    assert response.status_code == 403


def test_strava_token_encryption_round_trip():
    encrypted = encrypt_token('mi-token-secreto')
    assert encrypted != 'mi-token-secreto'
    assert decrypt_token(encrypted) == 'mi-token-secreto'
