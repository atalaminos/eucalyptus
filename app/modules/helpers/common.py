import re
import time
from typing import TYPE_CHECKING, List

from modules.helpers.conf import Conf
from modules.helpers.dnsserver_api import DnsserverDomainModel
from modules.helpers.nginx_manager_api import NginxProxyModel
from modules.helpers.portainer_api import PortainerStack, PortainerEndpoint
from utils.utils_log import UtilsLog
from utils.utils_network import UtilsNetwork

if TYPE_CHECKING:
    from manager import Manager


class Common:

    def __init__(self, manager:  "Manager"):
        self.manager = manager
        self.last_accesses_to_stacks = {}
        self.conf = Conf.get_conf()

    def dnsserver_add_domain_from_portainer_stack(self, stack: PortainerStack):

        domain = self.conf.get('DOMAIN')
        endpoints: List[PortainerEndpoint] = self.manager.portainer_api.get_endpoints()
        endpoint_name = None
        for endpoint in endpoints:
            if endpoint['Id'] == stack['EndpointId']:
                endpoint_name = endpoint['Name']

        if endpoint_name is None:
            UtilsLog.error(f'No encontrado nombre de endpoint para identificador {stack["EndpointId"]}')
            return

        # Si los contenedores son 0, entonces el stack está parado
        is_stopped = False

        # Si el portainer no está arrancado (Status = 1 es arrancado), se arranca
        if stack['Status'] != 1:
            is_stopped = True
            self.manager.portainer_api.start_stack_by_stack_id(stack['Id'])
            if not self.manager.common.portainer_wait_start_stack(stack):
                return

        port_init = self.conf.get('PORT_INIT_HTTP_OR_HTTPS')
        end_init = self.conf.get('PORT_END_HTTP_OR_HTTPS')

        # Volver a obtener el stack con los contenedores asociados
        stack = self.manager.portainer_api.get_stack_with_containers(stack['Name'])

        for container in stack['Containers']:
            for port in container['Ports']:
                if 'IP' not in port or 'PublicPort' not in port:
                    continue
                if not (port_init < port['PublicPort'] < end_init):
                    continue

                protocol = UtilsNetwork.check_protocol(port['IP'], port['PublicPort'])
                if protocol not in ('http', 'https'):
                    continue

                subdomain = f"{container['Names'][0][1:]}-{endpoint_name}-{port['PublicPort']}.{domain}"
                if self.manager.dnsserver_api.add_record(domain=subdomain):
                    UtilsLog.info(f'Agregado dominio a dnsserver: {subdomain}')

        # El contenedor estaba parado, por lo que volvemos a pararlo de nuevo
        if is_stopped:
            self.manager.portainer_api.stop_stack_by_stack_id(stack['Id'])

    def dnsserver_delete_domain(self, dnsserver_domain: DnsserverDomainModel):
        self.manager.dnsserver_api.delete_record(dnsserver_domain['domain'])
        print(f"Eliminado dominio de dnsserver: {dnsserver_domain['domain']}")

    def nginxmanager_add_proxy_from_portainer_stack(self, stack: PortainerStack):

        domain = self.conf.get('DOMAIN')
        endpoints = self.manager.portainer_api.get_endpoints()

        # Si los contenedores son 0, entonces el stack está parado
        is_stopped = False
        if len(stack['Containers']) == 0:
            is_stopped = True
            self.manager.portainer_api.start_stack_by_stack_id(stack['Id'])
            if not self.portainer_wait_start_stack(stack):
                return

        certificate_id = self.manager.nginx_manager_api.get_certificate_id_by_name(domain)
        port_init = self.conf.get('PORT_INIT_HTTP_OR_HTTPS')
        end_init = self.conf.get('PORT_END_HTTP_OR_HTTPS')

        # Volver a obtener el stack con los contenedores asociados
        stack = self.manager.portainer_api.get_stack_with_containers(stack['Name'])

        for container in stack['Containers']:
            for port in container['Ports']:

                if 'IP' not in port or 'PublicPort' not in port:
                    continue
                if not (port_init < port['PublicPort'] < end_init):
                    continue

                protocol = UtilsNetwork.check_protocol(port['IP'], port['PublicPort'])
                if protocol not in ('http', 'https'):
                    continue

                endpoint_name = None
                for endpoint in endpoints:
                    if endpoint['Id'] == stack['EndpointId']:
                        endpoint_name = endpoint['Name']

                if endpoint_name is None:
                    pass

                subdomain = f"{container['Names'][0][1:]}-{endpoint_name}-{port['PublicPort']}.{domain}"
                if self.manager.nginx_manager_api.add_proxy(
                    subdomain=subdomain,
                    protocol_nginx='https',
                    protocol_target=protocol,
                    ip=port["IP"],
                    port=port["PublicPort"],
                    certificate_id=certificate_id
                ):
                    UtilsLog.info(f'Agregado proxy a nginx proxy manager: {subdomain}')

        # El contenedor estaba parado, por lo que volvemos a pararlo de nuevo
        if is_stopped:
            self.manager.portainer_api.stop_stack_by_stack_id(stack['Id'])

    def nginxmanager_extract_container_name_from_log(self, line):
        match = re.search(r"\b([a-zA-Z0-9]+-\d+)-[a-zA-Z0-9-]*\.wg\.es\b", line)
        if match:
            return match.group(1).strip()
        return None

    def nginxmanager_delete_proxy(self, nginx_proxy: NginxProxyModel):
        self.manager.nginx_manager_api.delete_proxy_by_id(nginx_proxy['id'])

    def portainer_start_stack(self, stack):
        stack_id = stack["id"] if "id" in stack else stack['Id']
        self.manager.portainer_api.start_stack_by_stack_id(stack_id)

    def portainer_stop_stack(self, stack):
        stack_id = stack["id"] if "id" in stack else stack['Id']
        self.manager.portainer_api.stop_stack_by_stack_id(stack_id)

    def portainer_wait_start_stack(self, stack: PortainerStack) -> bool:
        intentos_maximo = 10
        intentos = 0
        while intentos < intentos_maximo:
            for container_started in self.manager.portainer_api.get_containers():
                if container_started['ResourceControlId'] == stack['ResourceControlId']:
                    return True
            intentos += 1
            time.sleep(1)
        return False

