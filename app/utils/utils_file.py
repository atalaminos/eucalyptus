import os
from datetime import datetime


class UtilsFile:

    @staticmethod
    def exists_directory(directory):
        return os.path.exists(directory)