import ast
import os

from typing import Optional, Union

from dotenv import load_dotenv

from modules.helpers.sqlite import Sqlite
from utils.utils_log import UtilsLog



def type_from_env(value: str):

    if value is None:
        return None

    if value.lower() in {"true", "false"}:
        return value.lower() == "true"

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, (list, dict)):
            return parsed
    except (ValueError, SyntaxError):
        pass

    return value


class Conf:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Conf, cls).__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self):
        if self.__initialized:
            return
        self.sqlite = Sqlite('../conf.sqlite')
        self.__initialized = True

    @staticmethod
    def get_conf():
        return Conf()

    def get(self, key: str) -> Optional[Union[str, float, int, bool, list, dict]]:
        value = self.sqlite.get(key)
        value = value if value is not None else os.getenv(key, None)
        value = type_from_env(value)
        if value is None:
            UtilsLog.error(f'Conf (get): {key} no es válido')
        return value

    def set(self, key: str, value: str) -> bool:
        if getattr(os.getenv(key, None), key, None) is None:
            UtilsLog.error(f'Conf (set): {key} no es válido')
            return False

        self.sqlite.set(key, value)
        return True

    def clear(self):
        return self.sqlite.truncate()
