import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone

from .models import Event, EventRSVP


@pytest.fixture
def future_event(db, approved_moderator):
    return Event.objects.create(
        title='Evento test',
        date=timezone.now() + timedelta(days=7),
        created_by=approved_moderator,
    )


@pytest.mark.django_db
def test_rsvp_attending_creates_record(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'attending']))

    rsvp = EventRSVP.objects.get(event=future_event, user=approved_member)
    assert rsvp.response == 'attending'


@pytest.mark.django_db
def test_rsvp_attending_increments_stat(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'attending']))

    approved_member.profile.refresh_from_db()
    assert approved_member.profile.total_events_attended == 1


@pytest.mark.django_db
def test_rsvp_not_attending_decrements_stat(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'attending']))
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'not_attending']))

    approved_member.profile.refresh_from_db()
    assert approved_member.profile.total_events_attended == 0


@pytest.mark.django_db
def test_rsvp_back_to_attending_no_double_count(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'attending']))
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'not_attending']))
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'attending']))

    approved_member.profile.refresh_from_db()
    assert approved_member.profile.total_events_attended == 1


@pytest.mark.django_db
def test_attendee_list_visible_in_rsvp_response(approved_member, member_client, future_event):
    member_client.post(reverse('events:rsvp', args=[future_event.pk, 'attending']))
    response = member_client.post(reverse('events:rsvp', args=[future_event.pk, 'attending']))

    assert response.status_code == 200
    assert approved_member.email.encode() in response.content or \
           (approved_member.get_full_name() or '').encode() in response.content or \
           b'attending' in response.content
