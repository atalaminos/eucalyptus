import ipaddress
import json


class UtilsType:

    @staticmethod
    def ip_v4(ip):
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_integer(value: any) -> bool:
        return type(value) is int

    @staticmethod
    def is_float(value: any) -> bool:
        return type(value) is float

    @staticmethod
    def is_bool(value: any) -> bool:
        return isinstance(value, bool)

    @staticmethod
    def is_str(value: any) -> bool:
        return isinstance(value, str)

    @staticmethod
    def is_list(value):
        return isinstance(value, list)

    @staticmethod
    def is_dict(value):
        return isinstance(value, dict)

    @staticmethod
    def is_enum(value: any, enum: any) -> bool:
        return True if value in list(enum.__members__.keys()) else False

    @staticmethod
    def is_array(array: any):
        return True if isinstance(array, list) else False

    @staticmethod
    def is_np_array(np_array: any):
        return True if type(np_array) is np.ndarray else False

    @staticmethod
    def is_json(data: any) -> bool:
        try:
            json.loads(data)
        except ValueError:
            return False
        return True