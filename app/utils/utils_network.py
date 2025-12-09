import socket
import statistics
from typing import Union, List, Literal

import ntplib
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.urllib3.disable_warnings(category=InsecureRequestWarning)
import ping3
import dns.resolver
import requests
import warnings

warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class UtilsNetwork:

    ##
    # En Windows no funciona el parámetro -w cuando la respuesta del destinatario es muy rápida
    ##
    @staticmethod
    def ping(ip_address_or_host: str, numbers=1, timeout_in_ms=50) -> bool:
        count = 0
        for i in range(0, numbers):
            if ping3.ping(ip_address_or_host, timeout=float(timeout_in_ms / 1000)) is not None:
                count += 1
        return True if count == numbers else False

    @staticmethod
    def latency_in_ms(ip_address_or_host: str) -> Union[float, None]:
        latency = ping3.ping(ip_address_or_host, unit='ms')
        if latency is not None:
            return latency
        return None

    @staticmethod
    def latencies_in_ms(ip_address_or_host, numbers=10, ignore_error=True) -> Union[List[float], None]:
        latencies = []
        for i in range(0, numbers):
            latency = UtilsNetwork.latency_in_ms(ip_address_or_host)
            if latency is None and not ignore_error:
                return None
            latencies.append(latency)
        return latencies

    @staticmethod
    def latency_mean_in_ms(ip_address_or_host, numbers=10, ignore_error=True) -> Union[float, None]:
        latencies = UtilsNetwork.latencies_in_ms(ip_address_or_host, numbers, ignore_error)
        if latencies is None or len(latencies) == 0:
            return None
        return round(statistics.mean(latencies), 4)

    @staticmethod
    def jitter_in_ms(ip_address_or_host, numbers=10, ignore_error=True):
        latencies = UtilsNetwork.latencies_in_ms(ip_address_or_host, numbers, ignore_error)
        media = sum(latencies) / len(latencies)
        suma_cuadrados = sum((x - media) ** 2 for x in latencies)
        return round((suma_cuadrados / len(latencies)) ** 0.5, 4)

    @staticmethod
    def is_port_dns(ip_address_or_host, port=53, timeout_in_ms=50) -> bool:
        try:
            resolver = dns.resolver.Resolver()
            resolver.lifetime = float(timeout_in_ms / 1000)
            resolver.nameservers = [ip_address_or_host]
            resolver.port = port
            resolver.resolve('google.com', 'A')
            return True

        except dns.exception.Timeout:
            return False
        except dns.exception.DNSException:
            return True
        except ConnectionRefusedError:
            return False
        except TimeoutError:
            return False

    @staticmethod
    def is_port_ntp(ip_address_or_host, port=123, timeout_in_ms=50) -> bool:
        client = ntplib.NTPClient()
        try:
            client.request(ip_address_or_host, port=port, timeout=timeout_in_ms)
            return True
        except ntplib.NTPException:
            return False

    @staticmethod
    def get_protocol_web_server(ip, port):
        try:
            requests.get(f'https://{ip}:{port}', verify=False, timeout=5, allow_redirects=False)
            return 'http'
        except Exception:
            try:
                requests.get(f'http://{ip}:{port}', verify=False, timeout=5, allow_redirects=False)
                return 'http'
            except Exception:
                return None

    @staticmethod
    def check_tcp(host, puerto):

        if host == '0.0.0.0':
            return False

        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.settimeout(2)
            tcp_socket.connect((host, puerto))
            tcp_socket.close()
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False

    @staticmethod
    def check_udp(host, puerto):

        if host == '0.0.0.0':
            return False

        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.settimeout(2)
            udp_socket.sendto(b'', (host, puerto))
            udp_socket.close()
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False

    @staticmethod
    def check_http(host, puerto):

        if host == '0.0.0.0':
            return False

        try:
            resp = requests.get(f'http://{host}:{puerto}', verify=False, timeout=2)
            if int(resp.status_code) >= 200:
                return True
            else:
                return False
        except:
            return False

    @staticmethod
    def check_https_redirection(ip, port) -> Literal['https', 'http', None]:

        try:
            response = requests.get(f'https://{ip}:{port}', allow_redirects=False, timeout=2)
            if response.status_code in [301, 302, 303, 307, 308]:
                if response.headers['Location'].startswith('https'):
                    return 'https'
        except:
            try:
                response = requests.get(f'http://{ip}:{port}', allow_redirects=False, timeout=2)
                if response.status_code in [301, 302, 303, 307, 308]:
                    if response.headers['Location'].startswith('https'):
                        return 'https'
            except:
                pass

        return None


    @staticmethod
    def check_http_redirection(ip, port) -> Literal['https', 'http', None]:
        try:
            response = requests.get(f'https://{ip}:{port}', allow_redirects=False, timeout=2)
            if response.status_code in [301, 302, 303, 307, 308]:
                if response.headers['Location'].startswith('http'):
                    return 'http'
        except:
            try:
                response = requests.get(f'http://{ip}:{port}', allow_redirects=False, timeout=2)
                if response.status_code in [301, 302, 303, 307, 308]:
                    if response.headers['Location'].startswith('http'):
                        return 'http'
            except:
                pass

        return None

    @staticmethod
    def check_https(host, puerto):
        try:
            resp = requests.get(f'https://{host}:{puerto}', verify=False, timeout=2)
            if int(resp.status_code) >= 200:
                return True
            else:
                return False
        except:
            return False

    @staticmethod
    def check_protocol(host, port):
        return 'https' if UtilsNetwork.check_https_redirection(host, port) else \
            'http' if UtilsNetwork.check_http_redirection(host, port) else \
            'https' if UtilsNetwork.check_https(host, port) else \
            'http' if UtilsNetwork.check_http(host, port) else \
            'tcp' if UtilsNetwork.check_tcp(host, port) else \
            'udp' if UtilsNetwork.check_udp(host, port) else 'none'
