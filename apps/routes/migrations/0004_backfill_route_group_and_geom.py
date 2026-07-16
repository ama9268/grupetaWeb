from django.contrib.gis.geos import LineString, Point
from django.db import migrations

from apps.groups.constants import DEFAULT_GROUP_SLUG


def backfill_route_group_and_geom(apps, schema_editor):
    Route = apps.get_model('routes', 'route')
    Group = apps.get_model('groups', 'Group')
    default_group = Group.objects.get(slug=DEFAULT_GROUP_SLUG)

    for route in Route.objects.filter(group__isnull=True):
        # Si la ruta ya está enlazada a un evento, hereda la grupeta de ESE evento
        # (más correcto que el valor por defecto); si no, cae a la grupeta por defecto.
        linked_event = route.events.first()
        route.group = linked_event.group if linked_event else default_group
        route.save(update_fields=['group'])

    for route in Route.objects.exclude(track_geojson__isnull=True):
        points = route.track_geojson
        if not points:
            continue
        coords = [(lon, lat) for lat, lon in points]
        update_fields = []
        if len(coords) >= 2:
            route.track_geom = LineString(coords, srid=4326)
            update_fields.append('track_geom')
        route.start_point = Point(coords[0][0], coords[0][1], srid=4326)
        update_fields.append('start_point')
        route.save(update_fields=update_fields)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0003_route_group_nullable'),
        # Necesaria para que el estado histórico del modelo Route incluya la
        # relación inversa `events` (Event.associated_route, related_name='events').
        ('events', '0006_event_group_not_null'),
    ]

    operations = [
        migrations.RunPython(backfill_route_group_and_geom, noop_reverse),
    ]
