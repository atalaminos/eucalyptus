import os
from datetime import datetime


class UtilsLog:

    @staticmethod
    def _ts():
        return datetime.now().isoformat(sep=' ', timespec='seconds')

    @staticmethod
    def debug(msg):
        if os.getenv('DEBUG', False):
            print(f"{UtilsLog._ts()} DEBUG - {msg}")

    @staticmethod
    def error(msg):
        print(f"{UtilsLog._ts()} ERROR - {msg}")

    @staticmethod
    def info(msg):
        print(f"{UtilsLog._ts()} INFO - {msg}")

    @staticmethod
    def warning(msg):
        print(f"{UtilsLog._ts()} WARNING - {msg}")