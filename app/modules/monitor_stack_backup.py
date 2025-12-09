import os
import platform
import socket
import time
from pathlib import Path

from manager import Manager
from modules.helpers.conf import Conf
from modules.helpers.cron_manager import start_cron
from modules.helpers.rclone_api import SUFFIX_CRYPT
from utils.utils_date import UtilsDate
from utils.utils_file import UtilsFile
from utils.utils_log import UtilsLog


class MonitorStackBackup:

    def __init__(self, manager: Manager):
        self.manager = manager
        self.conf = Conf.get_conf()

    def handler(self):
        UtilsLog.info(f"Arrancado MonitorStackBackup")
        if self.conf.get('MONITOR_STACK_BACKUP_ENABLED'):
            UtilsLog.info(f"Arrancado MonitorStackBackup")
            self.config_rclone()
            self.backup_stacks()

    def init(self):
        start_cron(self.handler,  self.conf.get('MONITOR_STACK_BACKUP_CRON'))
        self.clear()
        self.config_rclone()
        self.backup_stacks()
        self.clear()

    def clear(self):
        current_dir = Path(".")

        for file in current_dir.glob("*.zst"):
            file.unlink()

        for file in current_dir.glob("*.tar"):
            file.unlink()

    def config_rclone(self):

        self.manager.rclone_api.config_set()
        rclone_config = self.manager.rclone_api.config_show()
        UtilsLog.info(f"Configurados {len(rclone_config)} remotes en rclone: {[r for r in rclone_config.keys()]}")

    def backup_stacks(self):

        path_docker_data = self.conf.get('MONITOR_STACK_BACKUP_PATH_DOCKER_DATA')
        hostname = os.environ.get("HOSTNAME_HOST") if os.environ.get("HOSTNAME_HOST") != '' else socket.gethostname()
        remote_path = f'{hostname}/{UtilsDate.now_with_format_filename()}'
        if os.name == "nt":
            path_docker_data = '../docker_data'

        if not UtilsFile.exists_directory(path_docker_data):
            UtilsLog.error(f"Directorio {path_docker_data} no existe")
            return

        for stack in self.manager.portainer_api.get_stacks():
            local_path = f'{path_docker_data}/{stack["Name"]}'
            if UtilsFile.exists_directory(local_path):
                for remote in self.manager.rclone_api.config_show():
                    if remote.endswith(SUFFIX_CRYPT):

                        # Antes de hacer la copia de seguridad, para el stack completo
                        if stack['Status'] == 1:
                            self.manager.portainer_api.stop_stack_by_stack_id(stack['Id'])
                            time.sleep(1)

                        self.manager.rclone_api.mkdir(remote, remote_path)
                        self.manager.rclone_api.copy(remote, local_path, f'{remote_path}/')
                        UtilsLog.info(f'Copia de seguridad realizada en {remote} para {stack["Name"]}')

                        # La copia ha finalizado, arrancar de nuevo el stack
                        if stack['Status'] == 1:
                            self.manager.portainer_api.start_stack_by_stack_id(stack['Id'])
