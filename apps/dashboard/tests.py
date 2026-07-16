import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone

from apps.events.models import Event, EventRSVP


@pytest.mark.django_db
def test_dashboard_renders(member_client):
    response = member_client.get(reverse('dashboard:home'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_dashboard_next_event_attendees_only_confirmed(
    member_client, approved_member, approved_moderator, default_group
):
    event = Event.objects.create(
        title='Proxima salida',
        start_at=timezone.now() + timedelta(days=2),
        created_by=approved_moderator,
        group=default_group,
    )
    EventRSVP.objects.create(event=event, member=approved_member, response='si')
    EventRSVP.objects.create(event=event, member=approved_moderator, response='no')

    response = member_client.get(reverse('dashboard:home'))
    assert response.status_code == 200
    assert b'Proxima salida' in response.content
    # Solo el que confirmó 'si' entra en los avatares (el 'no' se excluye).
    attendees = response.context['next_event_attendees']
    assert len(attendees) == 1
    assert attendees[0].member == approved_member
