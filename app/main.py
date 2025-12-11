import os
import sys
import threading
import time

from dotenv import load_dotenv

from manager import Manager
from modules.monitor_clear import MonitorClear
from modules.monitor_container_updates import MonitorContainerUpdates
from modules.monitor_dnsserver_and_nginxmanager import MonitorDnsserverAndNginxManager
from modules.monitor_stack_awake import MonitorStackAwake
from modules.monitor_stack_backup import MonitorStackBackup
from modules.monitor_stack_sleep import MonitorStackSleep
from utils.utils_log import UtilsLog

load_dotenv()

if os.getenv('DEBUG') is None:
    UtilsLog.error('Archivo .env no existe')
    time.sleep(1)
    sys.exit(1)


manager = Manager()


if __name__ == "__main__":
    threads = [
        # threading.Thread(target=lambda: MonitorStackSleep(manager).init(), daemon=True),
        # threading.Thread(target=lambda: MonitorStackAwake(manager).init(), daemon=True),
        # threading.Thread(target=lambda: MonitorDnsserverAndNginxManager(manager).init(), daemon=True),
        # threading.Thread(target=lambda: MonitorContainerUpdates(manager).init(), daemon=True),
        threading.Thread(target=lambda: MonitorClear(manager).init(), daemon=True),
        # threading.Thread(target=lambda: MonitorStackBackup(manager).init(), daemon=True)
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()
