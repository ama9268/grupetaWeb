from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy, reverse

from apps.accounts.mixins import ApprovedUserMixin, ModeratorRequiredMixin
from .models import Event, EventRSVP
from .forms import EventForm


class EventListView(ApprovedUserMixin, ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        return Event.objects.select_related('created_by', 'associated_route').order_by('date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        ctx['upcoming'] = [e for e in ctx['events'] if e.date >= now]
        ctx['past'] = [e for e in ctx['events'] if e.date < now]
        return ctx


class EventDetailView(ApprovedUserMixin, DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        user_rsvp = None
        if self.request.user.is_authenticated:
            user_rsvp = EventRSVP.objects.filter(event=event, user=self.request.user).first()
        ctx['user_rsvp'] = user_rsvp
        ctx['attendees'] = event.rsvps.filter(
            response='attending'
        ).select_related('user').order_by('created_at')
        return ctx


class EventCreateView(ModeratorRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_create.html'
    success_url = reverse_lazy('events:list')

    def form_valid(self, form):
        event = form.save(commit=False)
        event.created_by = self.request.user
        event.save()
        messages.success(self.request, f'Evento "{event.title}" creado correctamente.')
        return redirect(self.success_url)


def rsvp_view(request, event_id, response):
    if request.method != 'POST':
        return redirect('events:detail', pk=event_id)

    event = get_object_or_404(Event, pk=event_id)
    if response not in ('attending', 'not_attending'):
        return redirect('events:detail', pk=event_id)

    try:
        rsvp = EventRSVP.objects.get(event=event, user=request.user)
        if rsvp.response != response:
            rsvp.response = response
            rsvp.save()
    except EventRSVP.DoesNotExist:
        rsvp = EventRSVP.objects.create(event=event, user=request.user, response=response)

    attendees = event.rsvps.filter(response='attending').select_related('user').order_by('created_at')
    return render(request, 'events/partials/rsvp_widget.html', {
        'event': event,
        'user_rsvp': rsvp,
        'attendees': attendees,
    })
