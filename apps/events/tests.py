import pytest
from datetime import timedelta
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.groups.constants import DEFAULT_GROUP_SLUG
from apps.groups.models import Group
from apps.media_gallery.models import Album
from .models import Event, EventRSVP


def _default_group():
    return Group.objects.get(slug=DEFAULT_GROUP_SLUG)


@pytest.fixture
def future_event(db, approved_moderator):
    # OTRO (no ruta_especial): estas pruebas ejercitan RSVP/aceptar/cancelar/media, que
    # son acciones compartidas con Salidas y no dependen del tipo — usar un tipo gestionable
    # desde `events:detail`/`events:edit` evita acoplar estos tests a la sección Salidas
    # (ver test_salidas.py / la sección "Eventos vs Salidas" en apps/events/CLAUDE.md).
    return Event.objects.create(
        title='Evento test',
        event_type=Event.EventType.OTRO,
        start_at=timezone.now() + timedelta(days=7),
        created_by=approved_moderator, group=_default_group(),
    )


# --- RSVP ---

@pytest.mark.django_db
def test_rsvp_si_creates_record(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'si']))
    rsvp = EventRSVP.objects.get(event=future_event, member=approved_member)
    assert rsvp.response == 'si'


@pytest.mark.django_db
def test_rsvp_si_increments_stat(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'si']))
    approved_member.profile.refresh_from_db()
    assert approved_member.profile.total_events_attended == 1


@pytest.mark.django_db
def test_rsvp_no_decrements_stat(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'si']))
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'no']))
    approved_member.profile.refresh_from_db()
    assert approved_member.profile.total_events_attended == 0


@pytest.mark.django_db
def test_rsvp_quizas_does_not_count(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'quizas']))
    approved_member.profile.refresh_from_db()
    assert approved_member.profile.total_events_attended == 0


@pytest.mark.django_db
def test_rsvp_back_to_si_no_double_count(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'si']))
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'no']))
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'si']))
    approved_member.profile.refresh_from_db()
    assert approved_member.profile.total_events_attended == 1


@pytest.mark.django_db
def test_attendee_list_visible_in_rsvp_response(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'si']))
    response = member_client.post(reverse('events:rsvp', args=[future_event.pk, 'si']))
    assert response.status_code == 200
    assert approved_member.email.encode() in response.content


@pytest.mark.django_db
def test_rsvp_requires_approved_user(client, future_event):
    # Usuario anónimo no puede hacer RSVP.
    response = client.post(reverse('events:rsvp', args=[future_event.pk, 'si']))
    assert response.status_code in (302, 403)
    assert not EventRSVP.objects.exists()


# --- Permisos de creación / moderación ---

@pytest.mark.django_db
def test_member_cannot_create_event(member_client):
    response = member_client.get(reverse('events:create'))
    assert response.status_code == 403


@pytest.mark.django_db
def test_moderator_can_create_event(moderator_client):
    response = moderator_client.post(reverse('events:create'), {
        'group': _default_group().pk,
        'title': 'Salida al puerto',
        'event_type': 'otro',
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'description': '',
        'location': '',
    })
    assert response.status_code == 302
    assert Event.objects.filter(title='Salida al puerto', state='pendiente').exists()


@pytest.mark.django_db
def test_member_cannot_accept_event(member_client, future_event):
    response = member_client.post(reverse('events:accept', args=[future_event.pk]))
    assert response.status_code == 403
    future_event.refresh_from_db()
    assert future_event.state == 'pendiente'


# --- Transiciones de estado ---

@pytest.mark.django_db
def test_accept_sets_state_and_creates_album(moderator_client, future_event):
    moderator_client.post(reverse('events:accept', args=[future_event.pk]))
    future_event.refresh_from_db()
    assert future_event.state == 'aceptado'
    assert Album.objects.filter(event=future_event).count() == 1


@pytest.mark.django_db
def test_accept_is_idempotent_album(moderator_client, future_event):
    moderator_client.post(reverse('events:accept', args=[future_event.pk]))
    moderator_client.post(reverse('events:accept', args=[future_event.pk]))
    assert Album.objects.filter(event=future_event).count() == 1


@pytest.mark.django_db
def test_event_update_deletes_old_image(moderator_client, approved_moderator):
    from unittest.mock import patch
    from django.core.files.uploadedfile import SimpleUploadedFile
    event = Event.objects.create(
        title='Con imagen', start_at=timezone.now() + timedelta(days=3),
        created_by=approved_moderator, group=_default_group(), image_public_id='old_id', image_url='http://old',
    )
    png = SimpleUploadedFile('f.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 253, content_type='image/png')
    with patch('apps.events.views.upload_image', return_value=('new_id', 'http://new')), \
         patch('apps.events.views.delete_asset') as mock_delete:
        resp = moderator_client.post(reverse('events:edit', args=[event.pk]), {
            'title': 'Con imagen', 'event_type': 'otro',
            'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
            'image': png,
        })
    assert resp.status_code == 302
    event.refresh_from_db()
    assert event.image_public_id == 'new_id'
    mock_delete.assert_called_once_with('old_id')


@pytest.mark.django_db
def test_event_update_without_new_image_keeps_old(moderator_client, approved_moderator):
    from unittest.mock import patch
    event = Event.objects.create(
        title='Sin cambio de imagen', start_at=timezone.now() + timedelta(days=3),
        created_by=approved_moderator, group=_default_group(), image_public_id='keep_id', image_url='http://keep',
    )
    with patch('apps.events.views.delete_asset') as mock_delete:
        moderator_client.post(reverse('events:edit', args=[event.pk]), {
            'title': 'Sin cambio de imagen', 'event_type': 'otro',
            'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        })
    event.refresh_from_db()
    assert event.image_public_id == 'keep_id'
    mock_delete.assert_not_called()


@pytest.mark.django_db
def test_event_creation_creates_chat_room(future_event):
    future_event.refresh_from_db()
    assert future_event.chat_room is not None
    assert future_event.chat_room.category == 'eventos'
    assert future_event.chat_room.slug == f'evento-{future_event.pk}'


@pytest.mark.django_db
def test_cancel_archives_event(moderator_client, future_event):
    moderator_client.post(reverse('events:cancel', args=[future_event.pk]))
    future_event.refresh_from_db()
    assert future_event.state == 'cancelado'
    assert future_event.is_archived is True
    assert future_event.chat_room.is_archived is True


@pytest.mark.django_db
def test_update_event_states_command(db, approved_moderator):
    past = timezone.now() - timedelta(days=1)
    pendiente = Event.objects.create(
        title='Pasado pendiente', start_at=past, created_by=approved_moderator, group=_default_group(),
        state=Event.State.PENDIENTE,
    )
    aceptado = Event.objects.create(
        title='Pasado aceptado', start_at=past, created_by=approved_moderator, group=_default_group(),
        state=Event.State.ACEPTADO,
    )
    call_command('update_event_states')
    pendiente.refresh_from_db()
    aceptado.refresh_from_db()
    assert pendiente.state == 'superado'
    assert aceptado.state == 'realizado'


# --- Listado / filtros ---

@pytest.mark.django_db
def test_list_default_filter_shows_only_active(moderator_client, approved_moderator):
    Event.objects.create(title='PendVisibleXYZ', start_at=timezone.now() + timedelta(days=1),
                         created_by=approved_moderator, group=_default_group(), state=Event.State.PENDIENTE)
    Event.objects.create(title='CancelHiddenXYZ', start_at=timezone.now() + timedelta(days=1),
                         created_by=approved_moderator, group=_default_group(), state=Event.State.CANCELADO)
    response = moderator_client.get(reverse('events:list'))
    assert b'PendVisibleXYZ' in response.content
    assert b'CancelHiddenXYZ' not in response.content


@pytest.mark.django_db
def test_list_filter_by_state(moderator_client, approved_moderator):
    Event.objects.create(title='CanceladoUnoXYZ', start_at=timezone.now() + timedelta(days=1),
                         created_by=approved_moderator, group=_default_group(), state=Event.State.CANCELADO)
    response = moderator_client.get(reverse('events:list'), {'estado': 'cancelado'})
    assert b'CanceladoUnoXYZ' in response.content


# --- Subida de media ---

@pytest.mark.django_db
def test_media_upload_blocked_without_album(member_client, future_event):
    # Evento pendiente aún no tiene álbum: no se permite subir.
    from apps.media_gallery.models import MediaItem
    response = member_client.post(reverse('events:media_upload', args=[future_event.pk]))
    assert response.status_code == 302
    assert not MediaItem.objects.exists()


@pytest.mark.django_db
def test_media_upload_rejects_oversized_file(moderator_client, future_event, settings):
    # Con álbum (evento aceptado), un archivo que supera el límite no se sube.
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.media_gallery.models import MediaItem
    settings.MAX_IMAGE_UPLOAD_SIZE = 100  # bytes
    moderator_client.post(reverse('events:accept', args=[future_event.pk]))
    png = SimpleUploadedFile(
        'foto.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 253, content_type='image/png'
    )
    response = moderator_client.post(
        reverse('events:media_upload', args=[future_event.pk]),
        {'media_type': 'image', 'file': png},
    )
    assert response.status_code == 302
    assert not MediaItem.objects.exists()


# --- Render de la ficha de evento ---

@pytest.mark.django_db
def test_detail_renders(member_client, future_event):
    response = member_client.get(reverse('events:detail', args=[future_event.pk]))
    assert response.status_code == 200
    assert b'rsvp-widget' in response.content


@pytest.mark.django_db
def test_detail_renders_with_route(member_client, approved_moderator):
    from apps.routes.models import Route
    route = Route.objects.create(
        group=_default_group(), title='Ruta del puerto', author=approved_moderator,
        track_geojson=[[40.4, -3.7], [40.5, -3.6]],
    )
    event = Event.objects.create(
        title='Con ruta', start_at=timezone.now() + timedelta(days=2),
        created_by=approved_moderator, group=_default_group(), associated_route=route,
    )
    response = member_client.get(reverse('events:detail', args=[event.pk]))
    assert response.status_code == 200
    assert b'route-map' in response.content


@pytest.mark.django_db
def test_detail_renders_accepted_with_album(moderator_client, future_event):
    moderator_client.post(reverse('events:accept', args=[future_event.pk]))
    response = moderator_client.get(reverse('events:detail', args=[future_event.pk]))
    assert response.status_code == 200
    # Con álbum y no archivado, aparece el formulario de subida.
    assert b'events:media_upload' not in response.content  # es una URL resuelta, no el nombre
    assert b'Subir a la galer' in response.content


# --- Ruta al crear/editar evento: elegir existente vs subir GPX nuevo ---

MINIMAL_GPX = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1" creator="test">
  <trk><trkseg>
    <trkpt lat="40.4168" lon="-3.7038"><ele>650</ele><time>2024-06-01T09:00:00Z</time></trkpt>
    <trkpt lat="40.4200" lon="-3.7000"><ele>680</ele><time>2024-06-01T09:05:00Z</time></trkpt>
    <trkpt lat="40.4250" lon="-3.6950"><ele>670</ele><time>2024-06-01T09:12:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""


def _gpx_upload(name='ruta.gpx'):
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, MINIMAL_GPX, content_type='application/gpx+xml')


@pytest.mark.django_db
def test_create_event_with_new_gpx_creates_and_links_route(moderator_client, approved_moderator):
    from apps.routes.models import Route
    response = moderator_client.post(reverse('events:create'), {
        'group': _default_group().pk,
        'title': 'Marcha con GPX',
        'event_type': 'otro',
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'description': 'Descripción de la marcha',
        'location': '',
        'route_mode': 'new',
        'gpx_file': _gpx_upload(),
    })
    assert response.status_code == 302
    event = Event.objects.get(title='Marcha con GPX')
    # Se creó una Route real, asociada, con autor = creador y datos del evento.
    assert event.associated_route is not None
    route = event.associated_route
    assert route.author == approved_moderator
    assert route.title == 'Marcha con GPX'
    assert route.description == 'Descripción de la marcha'
    assert route.distance_km is not None and route.distance_km > 0
    # Es una ruta normal, visible en el módulo Rutas.
    assert Route.objects.filter(pk=route.pk).exists()


@pytest.mark.django_db
def test_create_event_with_existing_route_does_not_create_route(moderator_client, approved_moderator):
    from apps.routes.models import Route
    route = Route.objects.create(group=_default_group(), title='Ruta ya existente', author=approved_moderator)
    before = Route.objects.count()
    response = moderator_client.post(reverse('events:create'), {
        'group': _default_group().pk,
        'title': 'Evento con ruta existente',
        'event_type': 'otro',
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'description': '',
        'location': '',
        'route_mode': 'existing',
        'associated_route': route.pk,
    })
    assert response.status_code == 302
    event = Event.objects.get(title='Evento con ruta existente')
    assert event.associated_route_id == route.pk
    assert Route.objects.count() == before  # no se creó ninguna ruta nueva


@pytest.mark.django_db
def test_create_event_mode_none_has_no_route(moderator_client):
    response = moderator_client.post(reverse('events:create'), {
        'group': _default_group().pk,
        'title': 'Evento sin ruta',
        'event_type': 'otro',
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'description': '',
        'location': '',
        'route_mode': 'none',
    })
    assert response.status_code == 302
    event = Event.objects.get(title='Evento sin ruta')
    assert event.associated_route is None


@pytest.mark.django_db
def test_create_event_new_mode_invalid_gpx_creates_nothing(moderator_client):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.routes.models import Route
    bad = SimpleUploadedFile('trampa.gpx', b'esto no es un gpx', content_type='application/gpx+xml')
    response = moderator_client.post(reverse('events:create'), {
        'group': _default_group().pk,
        'title': 'Evento GPX malo',
        'event_type': 'otro',
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'description': '',
        'location': '',
        'route_mode': 'new',
        'gpx_file': bad,
    })
    assert response.status_code == 200  # re-renderiza el formulario con error
    assert not Event.objects.filter(title='Evento GPX malo').exists()
    assert not Route.objects.exists()


@pytest.mark.django_db
def test_edit_event_switch_existing_to_new_gpx_replaces_route(moderator_client, approved_moderator):
    from apps.routes.models import Route
    old = Route.objects.create(group=_default_group(), title='Ruta vieja', author=approved_moderator)
    event = Event.objects.create(
        title='Evento editable', start_at=timezone.now() + timedelta(days=4),
        created_by=approved_moderator, group=_default_group(), associated_route=old,
    )
    response = moderator_client.post(reverse('events:edit', args=[event.pk]), {
        'title': 'Evento editable',
        'event_type': 'otro',
        'start_at': (timezone.now() + timedelta(days=4)).strftime('%Y-%m-%dT%H:%M'),
        'description': '',
        'location': '',
        'route_mode': 'new',
        'gpx_file': _gpx_upload('nueva.gpx'),
    })
    assert response.status_code == 302
    event.refresh_from_db()
    assert event.associated_route_id != old.pk  # se reemplazó por la nueva
    assert event.associated_route.title == 'Evento editable'
    # La ruta antigua sigue existiendo en el módulo Rutas (SET_NULL, no se borra).
    assert Route.objects.filter(pk=old.pk).exists()


@pytest.mark.django_db
def test_edit_event_mode_none_clears_route(moderator_client, approved_moderator):
    from apps.routes.models import Route
    route = Route.objects.create(group=_default_group(), title='Ruta a soltar', author=approved_moderator)
    event = Event.objects.create(
        title='Evento a limpiar', start_at=timezone.now() + timedelta(days=4),
        created_by=approved_moderator, group=_default_group(), associated_route=route,
    )
    response = moderator_client.post(reverse('events:edit', args=[event.pk]), {
        'title': 'Evento a limpiar',
        'event_type': 'otro',
        'start_at': (timezone.now() + timedelta(days=4)).strftime('%Y-%m-%dT%H:%M'),
        'description': '',
        'location': '',
        'route_mode': 'none',
    })
    assert response.status_code == 302
    event.refresh_from_db()
    assert event.associated_route is None
    assert Route.objects.filter(pk=route.pk).exists()


# --- Eventos / Salidas: misma tabla, dos secciones (ver apps/events/CLAUDE.md, "Salidas") ---

@pytest.fixture
def future_salida(db, approved_moderator):
    return Event.objects.create(
        title='Salida test', event_type=Event.EventType.RUTA_ESPECIAL,
        start_at=timezone.now() + timedelta(days=7),
        created_by=approved_moderator, group=_default_group(),
    )


@pytest.mark.django_db
def test_ruta_especial_not_in_events_list(moderator_client, future_salida):
    response = moderator_client.get(reverse('events:list'), {'estado': 'todos'})
    assert future_salida.title.encode() not in response.content


@pytest.mark.django_db
def test_ruta_especial_in_salidas_list(moderator_client, future_salida):
    response = moderator_client.get(reverse('salidas:list'), {'estado': 'todos'})
    assert future_salida.title.encode() in response.content


@pytest.mark.django_db
def test_events_detail_404_for_ruta_especial(member_client, future_salida):
    # Una salida no se ve desde /events/<pk>/ — solo desde /salidas/<pk>/.
    response = member_client.get(reverse('events:detail', args=[future_salida.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_salidas_detail_renders(member_client, future_salida):
    response = member_client.get(reverse('salidas:detail', args=[future_salida.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_events_edit_404_for_ruta_especial(moderator_client, future_salida):
    # Evita que /events/<pk>/editar/ reasigne por error event_type a través de EventForm.
    response = moderator_client.get(reverse('events:edit', args=[future_salida.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_salidas_edit_404_for_non_ruta_especial(moderator_client, future_event):
    response = moderator_client.get(reverse('salidas:edit', args=[future_event.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_event_type_ruta_especial_not_selectable_via_events_create(moderator_client):
    response = moderator_client.post(reverse('events:create'), {
        'group': _default_group().pk,
        'title': 'Intento de colar una salida',
        'event_type': 'ruta_especial',
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'description': '', 'location': '',
    })
    assert response.status_code == 200  # el formulario rechaza la opción, no está en choices
    assert not Event.objects.filter(title='Intento de colar una salida').exists()


@pytest.mark.django_db
def test_salidas_create_sets_ruta_especial_and_requires_pace_level(moderator_client):
    response = moderator_client.post(reverse('salidas:create'), {
        'group': _default_group().pk,
        'title': 'Salida del sábado',
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'description': '', 'location': 'Plaza Mayor',
        'route_mode': 'none',
        # sin pace_level: debe rechazarse.
    })
    assert response.status_code == 200
    assert not Event.objects.filter(title='Salida del sábado').exists()

    response = moderator_client.post(reverse('salidas:create'), {
        'group': _default_group().pk,
        'title': 'Salida del sábado',
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'description': '', 'location': 'Plaza Mayor', 'pace_level': 'medio',
        'route_mode': 'none',
    })
    assert response.status_code == 302
    salida = Event.objects.get(title='Salida del sábado')
    assert salida.event_type == Event.EventType.RUTA_ESPECIAL
    assert salida.pace_level == 'medio'


@pytest.mark.django_db
def test_member_cannot_create_salida(member_client):
    response = member_client.get(reverse('salidas:create'))
    assert response.status_code == 403


@pytest.mark.django_db
def test_get_absolute_url_routes_by_type(future_event, future_salida):
    assert future_event.get_absolute_url() == reverse('events:detail', args=[future_event.pk])
    assert future_salida.get_absolute_url() == reverse('salidas:detail', args=[future_salida.pk])


@pytest.mark.django_db
def test_rsvp_works_from_salidas_section(approved_member, member_client, future_salida):
    # Acción compartida (no duplicada por sección): apuntarse funciona igual en una salida.
    response = member_client.post(reverse('events:rsvp', args=[future_salida.pk, 'si']))
    assert response.status_code == 200
    rsvp = EventRSVP.objects.get(event=future_salida, member=approved_member)
    assert rsvp.response == 'si'
