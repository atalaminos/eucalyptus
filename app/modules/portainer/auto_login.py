import datetime
import functools
from typing import Callable, Any


def auto_login(func: Callable) -> Callable:
    """
    Decorador que ejecuta login automáticamente si han pasado 5 minutos
    desde el último login o si no hay token válido.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        # Verificar si existe last_login_time, si no, inicializarlo
        if not hasattr(self, 'last_login_time'):
            self.last_login_time = None

        # Verificar si necesita hacer login
        needs_login = (
                self.token is None or
                self.last_login_time is None or
                (datetime.datetime.now() - self.last_login_time).total_seconds() > 300  # 5 minutos = 300 segundos
        )

        if needs_login:
            if self.login():
                self.last_login_time = datetime.datetime.now()
            else:
                raise Exception("No se pudo realizar el login automático")

        # Ejecutar la función original
        return func(self, *args, **kwargs)

    return wrapper