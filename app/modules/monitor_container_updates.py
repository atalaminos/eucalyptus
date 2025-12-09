import time
from typing import List

from manager import Manager
from modules.helpers.conf import Conf
from modules.helpers.cron_manager import start_cron
from modules.helpers.portainer_api import PortainerStack
from utils.utils_log import UtilsLog
from utils.utils_telegram import UtilsTelegram


class MonitorContainerUpdates:

    def __init__(self, manager: Manager):
        self.manager = manager
        self.conf = Conf()

    def handler(self):
        if self.conf.get('MONITOR_CONTAINER_UPDATES_ENABLED'):
            UtilsLog.info(f"Arrancado MonitorContainerUpdates")
            self.update_images()

    def init(self):
        start_cron(self.handler,  self.conf.get('MONITOR_CONTAINER_UPDATES_CRON'))

    def update_images(self):
        stacks: List[PortainerStack] = self.manager.portainer_api.get_stacks_with_containers()
        for stack in stacks:

            is_stopped = False
            if stack['Status'] == 2:
                self.manager.portainer_api.start_stack_by_stack_id(stack['Id'])
                is_stopped = True
                time.sleep(1)
                stack = self.manager.portainer_api.get_stack_with_containers(stack['Name'])
                if stack is None:
                    continue

            for container in stack['Containers']:
                image_id_local = container['ImageID']
                image_name = container['Image']

                self.manager.portainer_api.download_latest_image_by_image_name(image_name, with_dockerhub_auth=True)
                image = self.manager.portainer_api.get_image_info_by_name(image_name)
                if image is not None:
                    if image_id_local != image['Id']:
                        msg = f'{stack["Name"]} ({image_name}) actualizado'
                        UtilsLog.info(msg)
                        UtilsTelegram.enviar_mensaje(msg)

            if is_stopped:
                self.manager.portainer_api.stop_stack_by_stack_id(stack['Id'])
