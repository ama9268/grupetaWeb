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
def test_gpx_upload_backfills_difficulty_from_elevation(default_group, moderator_client):
    moderator_client.post(reverse('routes:create'), {
        'group': default_group.pk, 'title': 'Ruta con desnivel', 'gpx_file': _gpx_file(),
    })
    route = Route.objects.get(title='Ruta con desnivel')
    # El GPX de prueba solo sube 30 m -> nivel "suave" salvo que se elija a mano.
    assert route.difficulty in ('', Route.Difficulty.SUAVE)


@pytest.mark.django_db
def test_moderator_can_set_difficulty_on_create(default_group, moderator_client):
    moderator_client.post(reverse('routes:create'), {
        'group': default_group.pk, 'title': 'Ruta dura a mano',
        'difficulty': Route.Difficulty.DURA, 'gpx_file': _gpx_file(),
    })
    route = Route.objects.get(title='Ruta dura a mano')
    assert route.difficulty == Route.Difficulty.DURA


@pytest.mark.django_db
def test_route_defaults_to_recommendable_for_salidas():
    # Valor por defecto del modelo (una ruta nueva "en blanco", sin pasar por
    # ningún formulario): recomendable salvo que alguien la desmarque a mano.
    assert Route().recommendable_for_salidas is True


@pytest.mark.django_db
def test_unchecking_recommendable_checkbox_on_create_is_respected(default_group, moderator_client):
    # Un checkbox desmarcado no se envía en el POST (comportamiento estándar de
    # los formularios HTML) — hay que confirmar que eso se traduce en `False`,
    # no en el `default=True` del modelo.
    moderator_client.post(reverse('routes:create'), {
        'group': default_group.pk, 'title': 'Ruta de un viaje lejano', 'gpx_file': _gpx_file(),
    })
    route = Route.objects.get(title='Ruta de un viaje lejano')
    assert route.recommendable_for_salidas is False


@pytest.mark.django_db
def test_checking_recommendable_checkbox_on_create_is_saved(default_group, moderator_client):
    moderator_client.post(reverse('routes:create'), {
        'group': default_group.pk, 'title': 'Ruta local', 'gpx_file': _gpx_file(),
        'recommendable_for_salidas': 'on',
    })
    route = Route.objects.get(title='Ruta local')
    assert route.recommendable_for_salidas is True


@pytest.mark.django_db
def test_moderator_can_toggle_recommendable_on_edit(default_group, approved_moderator, moderator_client):
    route = Route.objects.create(
        group=default_group, title='Ruta a marcar', author=approved_moderator,
        recommendable_for_salidas=True,
    )
    response = moderator_client.post(reverse('routes:edit', args=[route.pk]), {
        'title': route.title, 'description': '', 'difficulty': '',
        # recommendable_for_salidas se omite -> checkbox desmarcado.
    })
    assert response.status_code == 302
    route.refresh_from_db()
    assert route.recommendable_for_salidas is False


@pytest.mark.django_db
def test_moderator_can_edit_own_group_route(default_group, approved_moderator, moderator_client):
    route = Route.objects.create(group=default_group, title='Ruta original', author=approved_moderator)
    response = moderator_client.post(reverse('routes:edit', args=[route.pk]), {
        'title': 'Ruta editada',
        'description': 'Nueva descripción',
        'difficulty': Route.Difficulty.MEDIA,
    })
    assert response.status_code == 302
    route.refresh_from_db()
    assert route.title == 'Ruta editada'
    assert route.description == 'Nueva descripción'
    assert route.difficulty == Route.Difficulty.MEDIA


@pytest.mark.django_db
def test_member_cannot_edit_route(default_group, approved_member, member_client):
    route = Route.objects.create(group=default_group, title='Ruta original', author=approved_member)
    response = member_client.post(reverse('routes:edit', args=[route.pk]), {
        'title': 'Hackeada', 'difficulty': Route.Difficulty.DURA,
    })
    assert response.status_code == 403
    route.refresh_from_db()
    assert route.title == 'Ruta original'


@pytest.mark.django_db
def test_moderator_of_other_group_cannot_edit_route(default_group, approved_moderator, moderator_client):
    other_group = Group.objects.create(name='Otra grupeta', slug='otra-grupeta-edit')
    from django.contrib.auth.models import User
    other_moderator = User.objects.create_user(
        username='mod-otra', email='mod-otra@test.com', password='testpass123', is_active=True,
    )
    Membership.objects.create(
        user=other_moderator, group=other_group,
        role=Membership.Role.MODERATOR, status=Membership.Status.APPROVED,
    )
    route = Route.objects.create(group=default_group, title='Ruta de A', author=approved_moderator)

    from django.test import Client
    other_client = Client()
    other_client.login(username='mod-otra', password='testpass123')
    response = other_client.post(reverse('routes:edit', args=[route.pk]), {'title': 'Hackeada'})
    # GroupModeratorRequiredMixin: existe y es visible, pero no la modera -> 403
    # (a diferencia del filtrado por queryset de RouteDetailView, que da 404).
    assert response.status_code == 403
    route.refresh_from_db()
    assert route.title == 'Ruta de A'


@pytest.mark.django_db
def test_moderator_can_delete_own_group_route(default_group, approved_moderator, moderator_client):
    route = Route.objects.create(group=default_group, title='Ruta a borrar', author=approved_moderator)
    response = moderator_client.post(reverse('routes:delete', args=[route.pk]))
    assert response.status_code == 302
    assert not Route.objects.filter(pk=route.pk).exists()


@pytest.mark.django_db
def test_member_cannot_delete_route(default_group, approved_member, member_client):
    route = Route.objects.create(group=default_group, title='Ruta protegida', author=approved_member)
    response = member_client.post(reverse('routes:delete', args=[route.pk]))
    assert response.status_code == 403
    assert Route.objects.filter(pk=route.pk).exists()


@pytest.mark.django_db
def test_route_delete_requires_post(default_group, approved_moderator, moderator_client):
    route = Route.objects.create(group=default_group, title='Ruta con GET', author=approved_moderator)
    response = moderator_client.get(reverse('routes:delete', args=[route.pk]))
    assert response.status_code == 302
    assert Route.objects.filter(pk=route.pk).exists()


@pytest.mark.django_db
def test_deleting_route_with_event_history_archives_instead_of_deleting(
    default_group, approved_moderator, moderator_client,
):
    from datetime import timedelta
    from django.utils import timezone
    from apps.events.models import Event

    route = Route.objects.create(group=default_group, title='Ruta de una Salida pasada', author=approved_moderator)
    event = Event.objects.create(
        title='Salida del domingo', group=default_group, created_by=approved_moderator,
        start_at=timezone.now() + timedelta(days=1), associated_route=route,
    )
    response = moderator_client.post(reverse('routes:delete', args=[route.pk]))
    assert response.status_code == 302

    # No se borra: se archiva. El evento sigue enlazado a la misma ruta.
    route.refresh_from_db()
    assert Route.objects.filter(pk=route.pk).exists()
    assert route.is_archived is True
    event.refresh_from_db()
    assert event.associated_route_id == route.pk


@pytest.mark.django_db
def test_moderator_can_toggle_is_archived_on_edit(default_group, approved_moderator, moderator_client):
    route = Route.objects.create(group=default_group, title='Ruta a archivar', author=approved_moderator)
    response = moderator_client.post(reverse('routes:edit', args=[route.pk]), {
        'title': route.title, 'description': '', 'difficulty': '',
        'is_archived': 'on',
    })
    assert response.status_code == 302
    route.refresh_from_db()
    assert route.is_archived is True

    # Reactivarla: se omite el checkbox -> False.
    response = moderator_client.post(reverse('routes:edit', args=[route.pk]), {
        'title': route.title, 'description': '', 'difficulty': '',
    })
    assert response.status_code == 302
    route.refresh_from_db()
    assert route.is_archived is False


@pytest.mark.django_db
def test_route_list_default_view_excludes_non_recommendable_and_archived(
    default_group, approved_member, member_client,
):
    Route.objects.create(group=default_group, title='Ruta local recomendable', author=approved_member)
    Route.objects.create(
        group=default_group, title='Ruta de viaje no recomendable', author=approved_member,
        recommendable_for_salidas=False,
    )
    Route.objects.create(
        group=default_group, title='Ruta archivada', author=approved_member, is_archived=True,
    )

    response = member_client.get(reverse('routes:list'))
    assert b'Ruta local recomendable' in response.content
    assert b'Ruta de viaje no recomendable' not in response.content
    assert b'Ruta archivada' not in response.content


@pytest.mark.django_db
def test_route_list_vista_todas_shows_everything(default_group, approved_member, member_client):
    Route.objects.create(group=default_group, title='Ruta A', author=approved_member)
    Route.objects.create(
        group=default_group, title='Ruta B no recomendable', author=approved_member,
        recommendable_for_salidas=False,
    )
    Route.objects.create(
        group=default_group, title='Ruta C archivada', author=approved_member, is_archived=True,
    )
    response = member_client.get(reverse('routes:list'), {'vista': 'todas'})
    assert b'Ruta A' in response.content
    assert b'Ruta B no recomendable' in response.content
    assert b'Ruta C archivada' in response.content


@pytest.mark.django_db
def test_route_list_vista_archivadas(default_group, approved_member, member_client):
    Route.objects.create(group=default_group, title='Ruta activa', author=approved_member)
    Route.objects.create(
        group=default_group, title='Ruta archivada visible', author=approved_member, is_archived=True,
    )
    response = member_client.get(reverse('routes:list'), {'vista': 'archivadas'})
    assert b'Ruta archivada visible' in response.content
    assert b'Ruta activa' not in response.content


@pytest.mark.django_db
def test_strava_connect_requires_moderator(member_client):
    response = member_client.get(reverse('routes:strava_connect'))
    assert response.status_code == 403


def test_strava_token_encryption_round_trip():
    encrypted = encrypt_token('mi-token-secreto')
    assert encrypted != 'mi-token-secreto'
    assert decrypt_token(encrypted) == 'mi-token-secreto'
