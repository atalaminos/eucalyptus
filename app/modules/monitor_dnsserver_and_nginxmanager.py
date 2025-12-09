import time

from manager import Manager
from modules.helpers.conf import Conf
from utils.utils_log import UtilsLog


class MonitorDnsserverAndNginxManager:

    def __init__(self, manager: Manager):
        self.manager = manager
        self.conf = Conf.get_conf()

    def init(self):

        while True:
            while self.conf.get('MONITOR_STACK_DNSSERVER_AND_NGINXMANAGER_ENABLED'):
                UtilsLog.info(f"Arrancado MonitorDnsserverAndNginxManager")
                self.check_portainer_and_dnsserver()
                self.check_portainer_and_nginx_manager()
                tiempo = self.conf.get('MONITOR_STACK_DNSSERVER_AND_NGINXMANAGER_TIME_CHECK_STACKS_IN_MINUTES')
                UtilsLog.info(f"Finalizado MonitorDnsserverAndNginxManager, esperando {tiempo} minutos")
                time.sleep(tiempo * 60)
            time.sleep(5)

    def check_portainer_and_dnsserver(self):

        dnsserver_records = self.manager.dnsserver_api.get_records(self.conf.get('DOMAIN'))
        portainer_stacks = self.manager.portainer_api.get_stacks_with_containers()

        # Buscar los dominios que son necesarios incluir en dnsserver
        for stack in portainer_stacks:
            if not any(d['domain'].startswith(stack['Name']) for d in dnsserver_records):
                self.manager.common.dnsserver_add_domain_from_portainer_stack(stack)

        # Buscar los dominios que son necesarios eliminar en dnsserver
        servers_fixed = self.conf.get('MONITOR_STACK_DNSSERVER_AND_NGINXMANAGER_SERVERS_FIXED')
        for dnsserver_record in dnsserver_records:
            found = any(dnsserver_record['domain'].startswith(portainer_stack['Name']) for portainer_stack in portainer_stacks) \
                    or any(server_fixed['domain'].startswith(dnsserver_record['domain']) for server_fixed in servers_fixed)
            if not found:
                self.manager.common.dnsserver_delete_domain(dnsserver_record)

        # Agregar servidores fijos si no lo están ya
        for server_fixed in servers_fixed:
            if not any(server_fixed['domain'] == dns['domain'] for dns in dnsserver_records):
                if self.manager.dnsserver_api.add_record(domain=server_fixed['domain']):
                    UtilsLog.info(f"Agregado dominio de servidor fijo en dnsserver: {server_fixed['domain']}")

    def check_portainer_and_nginx_manager(self):

        nginx_proxies = self.manager.nginx_manager_api.get_proxies()
        portainer_stacks = self.manager.portainer_api.get_stacks_with_containers()

        # Buscar los dominios que son necesarios incluir en nginx proxy manager
        for stack in portainer_stacks:
            is_found = any(
                proxy["domain"].startswith(stack["Name"])
                for proxy in nginx_proxies
            )

            if not is_found:
                self.manager.common.nginxmanager_add_proxy_from_portainer_stack(stack)

        # Buscar los dominios que son necesarios eliminar en nginx proxy manager
        servers_fixed = self.conf.get('MONITOR_STACK_DNSSERVER_AND_NGINXMANAGER_SERVERS_FIXED')
        for nginx_proxy in nginx_proxies:
            if not any(nginx_proxy['domain'].startswith(stack['Name']) for stack in portainer_stacks) \
                    and not any(server_fixed['domain'].startswith(nginx_proxy['domain']) for server_fixed in servers_fixed):
                self.manager.common.nginxmanager_delete_proxy(nginx_proxy)

        # Agregar servidores fijos si no lo están ya
        for server_fixed in servers_fixed:
            if not any(server_fixed['domain'] == p['domain'] for p in nginx_proxies):
                certificate_id = self.manager.nginx_manager_api.get_certificate_id_by_name(self.conf.get('DOMAIN'))
                self.manager.nginx_manager_api.add_proxy(
                    subdomain=server_fixed['domain'],
                    protocol_nginx='https',
                    protocol_target=server_fixed['protocol_target'],
                    ip=server_fixed["ip"],
                    port=server_fixed["port"],
                    certificate_id=certificate_id
                )
                UtilsLog.info(f"Agregado dominio de servidor fijo en nginx proxy manager: {server_fixed['domain']}")

