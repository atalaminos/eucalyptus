import json
import os
import sys
from enum import Enum
from typing import TypedDict, List, cast

import requests
from urllib3.exceptions import InsecureRequestWarning

from modules.helpers.conf import Conf
from utils.utils_log import UtilsLog

requests.urllib3.disable_warnings(category=InsecureRequestWarning)


class NginxManagerProxyEnable(Enum):
    enabled: 1
    disabled: 0


class NginxManagerCertificate(TypedDict):
    id: int
    nice_name: str


class NginxManagerProxyForwardScheme(Enum):
    http = 'http'
    https = 'https'



class NginxManagerProxy(TypedDict):
    id: int
    domain_names: List[str]
    forward_host: str
    forward_port: int
    forward_scheme: NginxManagerProxyForwardScheme
    enabled: NginxManagerProxyEnable
    http2_support: NginxManagerProxyEnable
    hsts_subdomains: NginxManagerProxyEnable
    allow_websocket_upgrade: NginxManagerProxyEnable


class NginxRedirectionOrProxyTypeEnum(Enum):
    web = 'web'
    tcp = 'tcp'
    udp = 'udp'


class NginxProxyModel(TypedDict):
    id: int
    proxy: bool
    domain: str
    ip: str
    port: int
    type: NginxRedirectionOrProxyTypeEnum


class NginxManagerApi:
    def __init__(self, endpoint=None, username=None, password=None):
        self.conf = Conf.get_conf()
        self.endpoint = endpoint if endpoint is not None else self.conf.get('NGINXMANAGER_ENDPOINT')
        self.username = username if username is not None else self.conf.get('NGINXMANAGER_USERNAME')
        self.password = password if password is not None else self.conf.get('NGINXMANAGER_PASSWORD')
        self.token = None

    def login(self) -> bool:
        try:
            url = self.endpoint + '/tokens'
            login_data = {'identity': self.username, 'secret': self.password}
            response = requests.post(url, json=login_data, verify=False)
            data = response.json()

            if 'token' not in data:
                UtilsLog.error(f'Nginxmanager (login): Autenticación incorrecta')
                sys.exit(1)

            self.token = data['token']
            return True
        except Exception as e:
            UtilsLog.error(f'Nginxmanager (login): {e}')
            return False

    def _get_headers(self):
        return {'Content-Type': 'application/json; charset=UTF-8', 'Authorization': 'Bearer ' + self.token}

    def add_proxy(self, subdomain, protocol_nginx, protocol_target, ip, port, certificate_id) -> bool:
        data = {
            "domain_names": [subdomain],
            "forward_scheme": protocol_target,
            "forward_host": ip,
            "forward_port": port,
            "certificate_id": 0,
            "allow_websocket_upgrade": 1,
        }

        if protocol_nginx == 'https':
            data['certificate_id'] = certificate_id
            data['ssl_forced'] = True
            data['hsts_enabled'] = True
            data['http2_support'] = True

        url = f'{self.endpoint}/nginx/proxy-hosts'
        try:
            response = requests.post(url, data=json.dumps(data), headers=self._get_headers())
            response_data = response.json()

            if response.status_code != 200:
                UtilsLog.error(f"NginxManagerApi (add_proxy): {response.json()['error']['message']}")
                return False

            return True if 'id' in response_data else False
        except Exception as e:
            UtilsLog.error(f'Nginxmanager (error): {e}')
            return False

    def delete_proxy_by_id(self, id) -> bool:
        url = f'{self.endpoint}/nginx/proxy-hosts/{id}'
        try:
            response = requests.delete(url, headers=self._get_headers())

            if response.status_code != 200:
                UtilsLog.error(f"NginxManagerApi (delete_proxy_by_id): {response.json()['error']['message']}")
                return False

            return True
        except Exception as e:
            UtilsLog.error(f'Nginxmanager (error): {e}')
            return False

    def get_certificates(self) -> List[NginxManagerCertificate]:
        url = f'{self.endpoint}/nginx/certificates'
        try:
            response = requests.get(url, headers=self._get_headers())
            return response.json()
        except Exception as e:
            UtilsLog.error(f'Nginxmanager (get_certificates): {e}')
            return []

    def get_certificate_id_by_name(self, name):
        try:
            certificates = self.get_certificates()
            if certificates is None or not isinstance(certificates, list):
                return None
            
            for certificate in certificates:
                if not isinstance(certificate, dict):
                    continue
                if certificate.get('nice_name') == name:
                    return certificate.get('id')
            return None
        except Exception as e:
            UtilsLog.error(f"Error en get_certificate_id_by_name: {str(e)}")
            return None

    def get_proxies(self) -> List[NginxManagerProxy]:
        url = f'{self.endpoint}/nginx/proxy-hosts?expand=owner,certificate'
        try:
            response = requests.get(url, headers=self._get_headers())
            return cast(
                list[NginxManagerProxy],
                cast(object, [
                    {
                        'id': proxy['id'],
                        'proxy': True,
                        'domain': proxy['domain_names'][-1],
                        'ip': proxy['forward_host'],
                        'port': proxy['forward_port'],
                        'type': NginxRedirectionOrProxyTypeEnum.web
                    }
                    for proxy in response.json()
                ])
            )
        except Exception as e:
            UtilsLog.error(f'Nginxmanager (get_proxies): {e}')
            return []

