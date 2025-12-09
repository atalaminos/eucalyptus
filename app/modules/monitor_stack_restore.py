import time

from manager import Manager
from modules.helpers.conf import Conf


class MonitorStackRestore:

    def __init__(self, manager: Manager):
        self.manager = manager
        self.conf = Conf.get_conf()

    def init(self):
        while True:
            while self.conf.get('MONITOR_STACK_RESTORE_ENABLED'):
                time.sleep(self.conf.get('MONITOR_STACK_RESTORE_TIME_CHECK_IN_MINUTES') * 60)
            time.sleep(5)
