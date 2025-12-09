import re
import sys
from typing import List, TypedDict

import requests
from glom import glom
from urllib3.exceptions import InsecureRequestWarning

from modules.helpers.conf import Conf
from utils.utils_log import UtilsLog

requests.urllib3.disable_warnings(category=InsecureRequestWarning)


class DnsserverRecord(TypedDict):
    id: int
    domain: str
    ip: str


class DnsserverDomainModel(TypedDict):
    domain: str
    ip: str


class DnsserverApi:
    def __init__(self, endpoint: str=None, username: str=None, password: str=None):
        self.conf = Conf.get_conf()
        self.endpoint = endpoint if endpoint is not None else self.conf.get('DNSSERVER_ENDPOINT')
        self.username = username if username is not None else self.conf.get('DNSSERVER_USERNAME')
        self.password = password if password is not None else self.conf.get('DNSSERVER_PASSWORD')
        self.token = None

    def login(self) -> bool:
        url = self.endpoint + f'/user/login?'
        response = requests.get(url, params={'user': self.username, 'pass':  self.password})
        try:
            data = response.json()
            if 'token' not in data:
                UtilsLog.error('Dnsserver (login): Autenticación incorrecta')
                sys.exit(1)
            self.token = data['token']
            return True
        except Exception as e:
            UtilsLog.error(f'Dnsserver (login): {e}')
            return False

    def add_record(self, domain: str) -> bool:
        url = self.endpoint + f'/zones/records/add'

        try:
            response = requests.get(url, params={
                'token': self.token,
                'zone': self.conf.get('DOMAIN'),
                'domain': domain,
                'ipAddress': re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', self.conf.get('NGINXMANAGER_ENDPOINT')),
                'type': 'A'
            })

            if response.json()['status'] == 'error':
                UtilsLog.error(f'Dnsserver (add_record) con {domain}: {response.json()["errorMessage"]}')
                return False

            return True

        except Exception as e:
            UtilsLog.error(f'Dnsserver (add_record) con {domain}: {e}')
            return False

    def delete_record(self, domain: str) -> bool:
        url = self.endpoint + f'/zones/records/delete'
        try:
            response = requests.get(url, params={
                'token': self.token,
                'zone': self.conf.get('DOMAIN'),
                'domain': domain,
                'ipAddress': re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', self.conf.get('NGINXMANAGER_ENDPOINT')),
                'type': 'A'
            })

            if response.json()['status'] == 'error':
                UtilsLog.error(f'Dnsserver (add_record): {response.json()["errorMessage"]}')
                return False

            return True

        except Exception as e:
            UtilsLog.error(f'Dnsserver (error delete_record): {e}')
            return False

    def get_records(self, domain_and_zone: str) -> List[DnsserverDomainModel]:
        url = self.endpoint + f'/zones/records/get'
        try:
            response = requests.get(url, params={
                'token': self.token,
                'domain': domain_and_zone,
                'zone': domain_and_zone,
                'listZone': True
            })

            if response.json()['status'] == 'error':
                UtilsLog.error(f'Dnsserver (get_records): {response.json()["errorMessage"]}')
                return []

            return [
                {
                    'domain': record['name'],
                    'ip': record['rData']['ipAddress']
                }
                for record in response.json()['response']['records']
                if glom(record, 'type', default=None) == 'A'
            ]
        except Exception as e:
            UtilsLog.error(f'Dnsserver (get_records): {e}')
            return []

