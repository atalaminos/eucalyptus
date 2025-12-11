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


def safe_init(monitor_class):
    try:
        monitor_class(manager).init()
    except Exception as e:
        UtilsLog.error(f"Error en {monitor_class.__name__}: {str(e)}")
        raise


if __name__ == "__main__":
    threads = [
        threading.Thread(target=lambda: safe_init(MonitorStackSleep), daemon=False),
        threading.Thread(target=lambda: safe_init(MonitorStackAwake), daemon=False),
        threading.Thread(target=lambda: safe_init(MonitorDnsserverAndNginxManager), daemon=False),
        threading.Thread(target=lambda: safe_init(MonitorContainerUpdates), daemon=False),
        threading.Thread(target=lambda: safe_init(MonitorClear), daemon=False),
        threading.Thread(target=lambda: safe_init(MonitorStackBackup), daemon=False)
    ]

    for t in threads:
        t.start()

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        UtilsLog.info("Apagando aplicación...")
        sys.exit(0)
