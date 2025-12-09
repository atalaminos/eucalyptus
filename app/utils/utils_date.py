import os
from datetime import datetime


class UtilsDate:

    @staticmethod
    def now_with_format_filename():
        return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")