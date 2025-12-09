import time

from manager import Manager
from modules.helpers.conf import Conf
from utils.utils_log import UtilsLog


class MonitorClear:

    def __init__(self, manager: Manager):
        self.manager = manager
        self.conf = Conf.get_conf()

    def init(self):
        while True:
            UtilsLog.info(f"Arrancado MonitorClear")
            while self.conf.get('MONITOR_CLEAR_ENABLED'):
                while self.clear_images() != 0:
                    time.sleep(1)
                tiempo = self.conf.get('MONITOR_CLEAR_TIME_CHECK_IN_MINUTES')
                UtilsLog.info(f"Finalizado MonitorClear, esperando {tiempo} minutos")
                time.sleep(tiempo * 60)
            time.sleep(5)

    def clear_images(self) -> int:
        num_deleted = 0
        for image in self.manager.portainer_api.get_images():
            if len(image['RepoTags']) == 0 and self.manager.portainer_api.delete_image_by_id(image['Id']):
                print(f'Eliminada imagen huérfana {image["Id"]}')
                num_deleted += 1
        return num_deleted
