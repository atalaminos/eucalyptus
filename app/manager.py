import sys

from dotenv import load_dotenv

from modules.helpers.common import Common
from modules.helpers.conf import Conf
from modules.helpers.dnsserver_api import DnsserverApi
from modules.helpers.nginx_manager_api import NginxManagerApi
from modules.helpers.portainer_api import PortainerApi
from modules.helpers.rclone_api import RcloneApi


class Manager:

    def __init__(self):

        conf = Conf.get_conf()

        self.portainer_api = PortainerApi(
            endpoint=conf.get('PORTAINER_ENDPOINT'),
            username=conf.get('PORTAINER_USERNAME'),
            password=conf.get('PORTAINER_PASSWORD'),
            endpoint_id=conf.get('PORTAINER_ENDPOINT_ID')
        )
        self.portainer_api.login()

        self.dnsserver_api = DnsserverApi(
            endpoint=conf.get('DNSSERVER_ENDPOINT'),
            username=conf.get('DNSSERVER_USERNAME'),
            password=conf.get('DNSSERVER_PASSWORD')
        )
        self.dnsserver_api.login()

        self.nginx_manager_api = NginxManagerApi(
            endpoint=conf.get('NGINXMANAGER_ENDPOINT'),
            username=conf.get('NGINXMANAGER_USERNAME'),
            password=conf.get('NGINXMANAGER_PASSWORD')
        )
        self.nginx_manager_api.login()
        self.rclone_api = RcloneApi()
        self.common = Common(self)
