from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='created_events'
    )
    associated_route = models.ForeignKey(
        'routes.Route', on_delete=models.SET_NULL, null=True, blank=True, related_name='events'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']
        indexes = [models.Index(fields=['date'])]

    def __str__(self):
        return f'{self.title} ({self.date.strftime("%d/%m/%Y")})'

    @property
    def is_upcoming(self):
        return self.date >= timezone.now()

    def attending_count(self):
        return self.rsvps.filter(response='attending').count()


class EventRSVP(models.Model):
    RSVP_CHOICES = [
        ('attending', 'Voy'),
        ('not_attending', 'No voy'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rsvps')
    response = models.CharField(max_length=20, choices=RSVP_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('event', 'user')]
