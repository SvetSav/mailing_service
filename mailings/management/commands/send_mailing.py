from django.core.management.base import BaseCommand, CommandError

from mailings.models import Mailing
from mailings.services import MailingSendError, send_mailing


class Command(BaseCommand):
    help = "Отправляет рассылку по её ID"

    def add_arguments(self, parser):
        parser.add_argument("mailing_id", type=int)

    def handle(self, *args, **options):
        mailing_id = options["mailing_id"]
        try:
            mailing = Mailing.objects.get(pk=mailing_id)
        except Mailing.DoesNotExist:
            raise CommandError(f"Рассылка с id={mailing_id} не найдена")

        mailing.update_status()

        try:
            attempts = send_mailing(mailing)
        except MailingSendError as exc:
            raise CommandError(str(exc))

        ok = sum(1 for a in attempts if a.status == "Успешно")
        self.stdout.write(
            self.style.SUCCESS(f"Рассылка #{mailing.pk}: успешно {ok}/{len(attempts)}")
        )
