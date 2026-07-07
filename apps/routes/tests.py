import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from .models import Route

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


@pytest.mark.django_db
def test_gpx_upload_extracts_stats(approved_member, member_client):
    gpx_file = SimpleUploadedFile('ruta.gpx', MINIMAL_GPX, content_type='application/gpx+xml')
    response = member_client.post(reverse('routes:create'), {
        'title': 'Ruta de prueba',
        'description': 'Test',
        'gpx_file': gpx_file,
    })

    assert response.status_code == 302
    route = Route.objects.get(title='Ruta de prueba')
    assert route.distance_km is not None and route.distance_km > 0
    assert route.elevation_gain_m is not None

    approved_member.profile.refresh_from_db()
    assert approved_member.profile.total_routes == 1
    assert approved_member.profile.total_km > 0


@pytest.mark.django_db
def test_route_detail_serializes_track_as_json_script(approved_member, member_client):
    route = Route.objects.create(
        title='Ruta con trazado', author=approved_member,
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
def test_route_detail_handles_missing_track(approved_member, member_client):
    route = Route.objects.create(title='Ruta sin trazado', author=approved_member)
    response = member_client.get(reverse('routes:detail', args=[route.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_gpx_upload_rejects_invalid_file(member_client):
    fake_gpx = SimpleUploadedFile('trampa.gpx', b'esto no es un gpx', content_type='application/gpx+xml')
    response = member_client.post(reverse('routes:create'), {
        'title': 'Ruta falsa',
        'description': '',
        'gpx_file': fake_gpx,
    })

    assert response.status_code == 200
    assert not Route.objects.filter(title='Ruta falsa').exists()
