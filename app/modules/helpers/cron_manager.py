from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from utils.utils_type import UtilsType


def start_cron(handler, expression_cron, misfire_grace_time=None):

    job_defaults = {'misfire_grace_time': 1200}
    if UtilsType.is_integer(misfire_grace_time) is not None:
        job_defaults['misfire_grace_time'] = misfire_grace_time

    scheduler = scheduler = BackgroundScheduler(job_defaults)

    campos = expression_cron.split()
    if len(campos) != 6:
        raise ValueError("Debes usar: segundo minuto hora día mes día_semana")

    segundo, minuto, hora, dia, mes, dow = campos

    trigger = CronTrigger(
        second=segundo,
        minute=minuto,
        hour=hora,
        day=dia,
        month=mes,
        day_of_week=dow
    )

    scheduler.add_job(handler, trigger)
    scheduler.start()

    return scheduler
