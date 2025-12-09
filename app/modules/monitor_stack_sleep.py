import time
from datetime import timedelta, datetime

from manager import Manager
from modules.helpers.conf import Conf
from modules.helpers.portainer_api import PortainerStack
from utils.utils_log import UtilsLog


class MonitorStackSleep:

    def __init__(self, manager: Manager):
        self.manager = manager
        self.conf = Conf.get_conf()

    def init(self):

        while True:
            while self.conf.get('MONITOR_STACK_SLEEP_ENABLED'):

                UtilsLog.info(f"Arrancado MonitorStackSleep")
                for stack in self.manager.portainer_api.get_stacks():
                    self.process_stack(stack)

                tiempo = self.conf.get('MONITOR_STACK_SLEEP_TIME_CHECK_STACKS_IN_MINUTES')
                UtilsLog.info(f"Finalizado MonitorStackSleep, esperando {tiempo} minutos")
                time.sleep(tiempo * 60)

            time.sleep(5)

    def process_stack(self, stack: PortainerStack):
        status_active = stack['Status'] == 1
        name_stack = stack["Name"]
        last_access = self.manager.common.last_accesses_to_stacks.get(stack['Name'], None)
        last_active_expired = last_access is None or (
                datetime.now() - last_access >= timedelta(minutes=self.conf.get('MONITOR_STACK_SLEEP_TIME_WITHOUT_ACTIVITY_BEFORE_STOP_IN_MINUTES'))
        )
        not_fixed_stack = name_stack not in self.conf.get('MONITOR_STACK_SLEEP_STACKS_FIXED')

        if self.conf.get('DEBUG'):
            UtilsLog.info(f'{name_stack}: {last_access}, fixed: {not not_fixed_stack}')

        if status_active and last_active_expired and not_fixed_stack:
            self.manager.common.portainer_stop_stack(stack)
            last_access = 'desconocido' if last_access is None else last_access
            UtilsLog.info(f"Stack {name_stack} parado (último acceso {last_access})")
            time.sleep(1)
