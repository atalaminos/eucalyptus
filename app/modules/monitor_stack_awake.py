import glob
import os
import time
from datetime import datetime
from typing import List

from manager import Manager
from modules.helpers.conf import Conf
from modules.helpers.portainer_api import PortainerStack
from utils.utils_log import UtilsLog


class MonitorStackAwake:

    def __init__(self, manager: Manager):
        self.manager = manager
        self.file_positions = {}
        self.conf = Conf.get_conf()

    def init(self):

        log_dir = '/logs'
        pattern = os.path.join(log_dir, "proxy-host-*_access.log")

        while True:

            UtilsLog.info(f"Arrancado MonitorStackAwake")
            while self.conf.get('MONITOR_STACK_AWAKE_ENABLED'):
                stacks = self.manager.portainer_api.get_stacks()
                log_files = glob.glob(pattern)
                for log_file in log_files:
                    if len(self.process_log(log_file, stacks)) > 0:
                        stacks = self.manager.portainer_api.get_stacks()
                tiempo = self.conf.get('MONITOR_STACK_AWAKE_TIME_CHECK_LOG_IN_SECONDS')
                time.sleep(tiempo)

            time.sleep(5)

    def process_log(self, log_file, stacks: List[PortainerStack]) -> list[str]:

        stacks_started = []

        if log_file not in self.file_positions:
            try:
                self.file_positions[log_file] = os.path.getsize(log_file)
            except Exception as e:
                UtilsLog.error(f'MonitorStackSleep (process_log): error abriendo el archivo {log_file} ({e})')
                self.file_positions[log_file] = 0

        try:
            with open(log_file, "r") as f:
                f.seek(self.file_positions[log_file])
                for line in f:

                    stack_names = [s["Name"] for s in stacks if "Name" in s]
                    stack_name = self.manager.common.nginxmanager_extract_container_name_from_log(line)

                    # Se ha detectado tráfico de un stack: se arranca si no lo está
                    if stack_name in stack_names and stack_name not in stacks_started:
                        self.manager.common.last_accesses_to_stacks[stack_name] = datetime.now()

                        # Si stack no está arrancado (Status = 1 es arrancado), se arranca
                        stack = next((s for s in stacks if s.get("Name") == stack_name), None)
                        if stack is not None and stack["Status"] != 1:
                            UtilsLog.info(f"MonitorStackSleep (process_log): Detectado tráfico en stack {stack_name}")
                            self.manager.common.portainer_start_stack(stack)
                            stacks_started.append(stack_name)
                            UtilsLog.info(f"MonitorStackSleep (process_log): iniciado stack {stack_name}")
                            time.sleep(1)

                self.file_positions[log_file] = f.tell()

        except FileNotFoundError:
            UtilsLog.error(f"MonitorStackSleep (process_log): archivo {log_file} no encontrado")
        except Exception as e:
            UtilsLog.error(f"MonitorStackSleep (process_log): {e}")

        return stacks_started

