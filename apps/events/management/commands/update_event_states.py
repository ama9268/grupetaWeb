from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.events.models import Event


class Command(BaseCommand):
    help = (
        'Actualiza los estados de los eventos según la fecha: los pendientes cuya '
        'fecha ha pasado pasan a "superado" y los aceptados a "realizado". '
        'Idempotente; pensado para ejecutarse periódicamente (cron de Dokploy).'
    )

    def handle(self, *args, **options):
        now = timezone.now()

        superados = Event.objects.filter(
            state=Event.State.PENDIENTE, start_at__lt=now
        ).update(state=Event.State.SUPERADO)

        realizados = Event.objects.filter(
            state=Event.State.ACEPTADO, start_at__lt=now
        ).update(state=Event.State.REALIZADO)

        self.stdout.write(self.style.SUCCESS(
            f'Eventos actualizados: {superados} → superado, {realizados} → realizado.'
        ))
