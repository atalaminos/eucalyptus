import json
import os
import sys
from enum import Enum
from typing import TypedDict, List, Optional

import requests
from urllib3.exceptions import InsecureRequestWarning

from modules.helpers.conf import Conf
from modules.portainer.auto_login import auto_login
from utils.utils_log import UtilsLog

requests.urllib3.disable_warnings(category=InsecureRequestWarning)


class PortainerEndpoint(TypedDict):
    Id: int
    Name: str


class PortainerContainerPortType(Enum):
    tcp = 'tcp'
    upd = 'upd'


class PortainerContainerPort(TypedDict):
    IP: str
    PrivatePort: int
    PublicPort: int
    Type: PortainerContainerPortType


class PortainerContainerMount(TypedDict):
    Destination: str
    Mode: str
    Propagation: str
    RW: bool
    Source: str
    Type: str


class PortainerContainer(TypedDict):
    Id: int
    Image: str
    ImageID: str
    Names: List[str]
    Ports: List[PortainerContainerPort]
    ResourceControlId: int
    Mounts: List[PortainerContainerMount]


class PortainerStack(TypedDict):
    Id: int
    Name: str
    EndpointId: int
    Status: int
    ResourceControlId: int
    Containers: List[PortainerContainer]


class PortainerImage(TypedDict):
    Id: int
    RepoTags: List[str]
    Created: str
    Size: int


class PortainerVolume(TypedDict):
    CreatedAt: str
    Driver: str
    Mountpoint: str
    Name: str
    ResourceID: str
    Scope: str


class PortainerApi:
    def __init__(self, endpoint=None, username=None, password=None, endpoint_id=None, timeout=None):
        self.conf = Conf.get_conf()
        self.endpoint = endpoint if endpoint is not None else self.conf.get('PORTAINER_ENDPOINT')
        self.username = username if username is not None else self.conf.get('PORTAINER_USERNAME')
        self.password = password if password is not None else self.conf.get('PORTAINER_PASSWORD')
        self.endpoint_id = endpoint_id if endpoint_id is not None else self.conf.get('PORTAINER_ENDPOINT_ID')
        self.timeout = timeout if timeout is not None else self.conf.get('PORTAINER_TIMEOUT')
        self.token = None

    def login(self) -> bool:
        url = self.endpoint + '/auth'
        login_data = {'Username': self.username, 'Password': self.password }
        try:
            response = requests.post(url, json=login_data, verify=False)
            data = response.json()
            if 'jwt' not in data:
                UtilsLog.error(f'Portainer - login: Autenticación incorrecta')
                sys.exit(1)
            self.token = data['jwt']
            return True
        except Exception as e:
            UtilsLog.error(f'Portainer (login): {e}')
            return False

    def _get_headers(self):
        return {'Authorization': 'Bearer ' + self.token}

    @auto_login
    def delete_image_by_id(self, image_id: str) -> bool:
        try:
            url = self.endpoint + f"/endpoints/{self.endpoint_id}/docker/images/{image_id}"
            response = requests.delete(url, headers=self._get_headers(), verify=False)

            if response.status_code not in [200, 204]:
                UtilsLog.debug(f"Portainer (delete_image_by_id): {response.json()['message']}")
                return False

            return True

        except Exception as e:
            UtilsLog.error(f'Portainer (delete_image_by_id): {e}')
            return False

    @auto_login
    def delete_container_by_id(self, container_id: str) -> bool:
        try:
            url = self.endpoint + f"/endpoints/{self.endpoint_id}/docker/containers/{container_id}"
            response = requests.delete(url, headers=self._get_headers(), verify=False)

            if response.status_code not in [200, 204]:
                UtilsLog.error(f"Portainer (delete_container_by_id): {response.json()['message']}")
                return False

            return True

        except Exception as e:
            UtilsLog.error(f'Portainer (delete_container_by_id): {e}')
            return False

    @auto_login
    def download_latest_image_by_image_name(self, image_reference, with_dockerhub_auth=False):
        try:
            # Si es un SHA256, necesitamos obtener el nombre real de la imagen
            if image_reference.startswith('sha256:'):
                image_name = self._get_image_name_from_sha(image_reference)
                if not image_name:
                    UtilsLog.error(
                        f"Portainer (download_latest_image): No se pudo obtener el nombre para SHA {image_reference}")
                    return False
            else:
                image_name = image_reference

            url = f"{self.endpoint}/endpoints/{self.endpoint_id}/docker/images/create"
            params = {"fromImage": image_name, "tag": "latest"}

            headers = self._get_headers()

            # Si no se proporciona registry_id, intentar obtener el de Docker Hub automáticamente
            if with_dockerhub_auth:
                registry_id = self.get_dockerhub_registry_id()

                # Añadir autenticación si hay registry_id
                # if registry_id:
                #     registry_auth = self._get_registry_auth(registry_id)
                #     if registry_auth:
                #         headers['X-Registry-Auth'] = registry_auth
                #     else:
                #         UtilsLog.warning(f"Portainer (download_latest_image): No se pudo obtener autenticación para registry {registry_id}")

            response = requests.post(
                url,
                headers=headers,
                params=params,
                stream=True,
                verify=False
            )

            if response.status_code != 200:
                error_msg = response.json().get('message', 'Unknown error')
                UtilsLog.error(f"Portainer (download_latest_image): {image_name} -> {error_msg}")
                return None

            last_line = None
            for line in response.iter_lines():
                if line:
                    last_line = line

            if not last_line:
                UtilsLog.error(f"Portainer (download_latest_image): {image_name} -> Error descargando la imagen")
                return False

            data = json.loads(last_line)
            status = data.get('status', '').lower()

            if 'up to date' in status or 'image is up to date' in status:
                UtilsLog.info(f'Portainer (download_latest_image): {image_name} -> No es necesario descargarla porque ya se cuenta con la última versión')
                return True

            if 'downloaded newer image' in status or 'pull complete' in status:
                UtilsLog.info(f'Portainer (download_latest_image): {image_name} -> Descargada última versión')
                return True

            if 'error' in data:
                UtilsLog.error(f"Portainer (download_latest_image): {image_name} -> {data['error']}")
                return False

            UtilsLog.error(
                f"Portainer (download_latest_image): {image_name} -> Error desconocido descargando imagen: {status}")
            return False

        except json.JSONDecodeError as e:
            UtilsLog.error(f"Portainer (download_latest_image): {image_reference} -> {e}")
            return False
        except Exception as e:
            UtilsLog.error(f"Portainer (download_latest_image): {image_reference} -> {e}")
            return False

    @auto_login
    def _get_image_name_from_sha(self, image_sha):
        try:
            url = f"{self.endpoint}/endpoints/{self.endpoint_id}/docker/images/{image_sha}/json"

            response = requests.get(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.error(f"Portainer (_get_image_name_from_sha): Error obteniendo info de {image_sha}")
                return None

            image_data = response.json()

            # Buscar en RepoTags
            repo_tags = image_data.get('RepoTags', [])
            if repo_tags and repo_tags[0] != '<none>:<none>':
                # Retornar solo el nombre sin el tag
                return repo_tags[0].split(':')[0]

            # Si no hay RepoTags, buscar en RepoDigests
            repo_digests = image_data.get('RepoDigests', [])
            if repo_digests:
                # Formato: 'nombre@sha256:...'
                return repo_digests[0].split('@')[0]

            UtilsLog.warning(f"Portainer (_get_image_name_from_sha): No se encontró nombre para {image_sha}")
            return None

        except Exception as e:
            UtilsLog.error(f"Portainer (_get_image_name_from_sha): {e}")
            return None

    @auto_login
    def _get_registry_auth(self, registry_id):
        try:
            url = f"{self.endpoint}/registries/{registry_id}"

            response = requests.get(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.error(f"Portainer (_get_registry_auth): Error obteniendo registro {registry_id}")
                return None

            registry_data = response.json()

            # Construir el objeto de autenticación
            auth_config = {
                "username": registry_data.get('Username', ''),
                "password": 'modemesd12A!',
                "serveraddress": registry_data.get('URL', 'https://index.docker.io/v1/')
            }

            # Codificar en base64
            import base64
            auth_json = json.dumps(auth_config)
            auth_base64 = base64.b64encode(auth_json.encode()).decode()

            return auth_base64

        except Exception as e:
            UtilsLog.error(f"Portainer (_get_registry_auth): {e}")
            return None

    @auto_login
    def get_dockerhub_registry_id(self):
        try:
            url = f"{self.endpoint}/registries"

            response = requests.get(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.error("Portainer (get_dockerhub_registry_id): Error obteniendo registros")
                return None

            registries = response.json()

            # Buscar Docker Hub (Type 1 = Docker Hub)
            for registry in registries:
                if registry.get('Type') == 6:
                    return registry.get('Id')

            UtilsLog.warning("Portainer (get_dockerhub_registry_id): No se encontró registro de Docker Hub")
            return None

        except Exception as e:
            UtilsLog.error(f"Portainer (get_dockerhub_registry_id): {e}")
            return None

    @auto_login
    def get_containers(self) -> List[PortainerContainer]:

        containers = []
        url = self.endpoint + f"/endpoints/{self.endpoint_id}/docker/containers/json?all=true"
        try:
            response = requests.get(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.error(f"Portainer (get_containers): {response.json()['message']}")
                return []

            containers += [
                PortainerContainer(
                    Id=container['Id'],
                    Image=container['Image'],
                    ImageID=container['ImageID'],
                    Names=container['Names'],
                    Ports=container['Ports'],
                    ResourceControlId=container['Portainer']['ResourceControl']['Id'],
                    Mounts=container['Mounts']
                )
                for container in response.json()
                if 'Portainer' in container
            ]

        except Exception as e:
            UtilsLog.error(f'Portainer (get_containers): {e}')
            return containers

        return containers

    @auto_login
    def get_endpoints(self) -> List[PortainerEndpoint]:
        url = self.endpoint + '/endpoints'
        try:
            response = requests.get(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.error(f"Portainer (get_endpoints): {response.json()['message']}")
                return []

            return [
                {
                    'Id': stack['Id'],
                    'Name': stack['Name']
                }
                for stack in response.json()
            ]

        except requests.exceptions.ReadTimeout as e:
            UtilsLog.error(f'Portainer (get_endpoints): {e}')
            return []
        except Exception as e:
            UtilsLog.error(f'Portainer (get_endpoints): {e}')
            return []

    @auto_login
    def get_images(self) -> List[PortainerImage]:

        images = []
        url = self.endpoint + f"/endpoints/{self.endpoint_id}/docker/images/json?all=true"
        try:
            response = requests.get(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.error(f"Portainer (get_images): {response.json()['message']}")
                return []

            images += [
                PortainerImage(
                    Id=image['Id'],
                    RepoTags=image['RepoTags'],
                    Created=image['Created'],
                    Size=image['Size'],
                    Labels=image['Labels']
                )
                for image in response.json()
            ]

        except Exception as e:
            UtilsLog.error(f'Portainer (get_images): {e}')
            return images

        return images

    @auto_login
    def get_image_info_by_name(self, image_name) -> Optional[PortainerImage]:
        try:
            url = self.endpoint + f"/endpoints/{self.endpoint_id}/docker/images/{image_name}/json"
            response = requests.get(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.error(f"Portainer (get_image_info_by_name): {response.json()['message']}")
                return None

            return response.json()

        except Exception as e:
            UtilsLog.error(f'Portainer (get_image_info_by_name): {e}')
            return None

    @auto_login
    def get_image_info_by_id(self, image_id) -> Optional[PortainerImage]:
        try:
            clean_id = image_id.replace('sha256:', '')
            url = self.endpoint + f'/endpoints/{self.endpoint_id}/docker/images/{clean_id}/json'
            response = requests.get(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.error(f"Portainer (get_image_info_by_id): {response.json()['message']}")
                return None

            return response.json()
        except Exception as e:
            UtilsLog.error(f'Portainer (get_image_info_by_id): {e}')
            return None

    @auto_login
    def get_stacks(self) -> List[PortainerStack]:

        stacks = []

        url = self.endpoint + '/stacks'
        try:
            response = requests.get(url, headers=self._get_headers(),verify=False)
            if response.status_code != 200:
                UtilsLog.error(f"Portainer (get_stacks): {response.json()['message']}")
                return []

            stacks += [
                PortainerStack(
                    Id=stack['Id'],
                    Name=stack['Name'],
                    EndpointId=stack['EndpointId'],
                    Status=stack['Status'],
                    ResourceControlId=stack['ResourceControl']['Id'],
                    Containers=[]
                )
                for stack in response.json() if stack['EndpointId'] == self.endpoint_id
            ]

        except requests.exceptions.ReadTimeout as e:
            UtilsLog.error(f'Portainer (get_stacks): {e}')
        except Exception as e:
            UtilsLog.error(f'Portainer (get_stacks): {e}')

        return stacks

    @auto_login
    def get_stack_with_containers(self, stack_name: str) -> Optional[PortainerStack]:
        try:
            stacks_with_containers = self.get_stacks_with_containers()
            for stack in stacks_with_containers:
                if stack['Name'] == stack_name:
                    return stack
            return None
        except Exception as e:
            UtilsLog.error(f'Portainer (get_stack_with_containers): {e}')
            return None

    @auto_login
    def get_stacks_with_containers(self) -> List[PortainerStack]:
        stacks = self.get_stacks()
        containers = self.get_containers()

        for stack in stacks:
            stack['Containers'] = []
            for container in containers:
                if stack['ResourceControlId'] == container['ResourceControlId']:
                    stack['Containers'].append(container)

        return stacks

    @auto_login
    def get_volumes(self) -> List[PortainerVolume]:

        volumes = []
        url = self.endpoint + f"/endpoints/{self.endpoint_id}/docker/volumes"
        try:
            response = requests.get(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.error(f"Portainer (get_volumes): {response.json()['message']}")
                return []

            volumes += [
                PortainerVolume(
                    CreatedAt=volume['CreatedAt'],
                    Mountpoint=volume['Mountpoint'],
                    Name=volume['Name'],
                    ResourceID=volume['ResourceID'],
                    Scope=volume['Scope'],
                    Driver=volume['Driver'],
                ) for volume in response.json()['Volumes']
            ]

        except Exception as e:
            UtilsLog.error(f'Portainer (get_volumes): {e}')
            return volumes

        return volumes

    @auto_login
    def start_stack_by_stack_id(self, stack_id) -> bool:
        try:
            url = self.endpoint + f'/stacks/{stack_id}/start?endpointId={self.endpoint_id}'
            response = requests.post(url, headers=self._get_headers(), verify=False)
            data = response.json()

            if 'message' in data and 'is already running' in data['message']:
                UtilsLog.info(f"Portainer (start_stack): {data['message']}")
                return True

            if response.status_code != 200:
                UtilsLog.error(f"Portainer (start_stack): {data['message']}")
                return False

            return True
        except Exception as e:
            UtilsLog.error(f'Portainer (start_stack): {e}')
            return False

    @auto_login
    def stop_stack_by_stack_id(self, stack_id) -> bool:
        try:
            url = self.endpoint + f'/stacks/{stack_id}/stop?endpointId={self.endpoint_id}'
            response = requests.post(url, headers=self._get_headers(), verify=False)

            if response.status_code != 200:
                UtilsLog.info(response.json())
                UtilsLog.error(f"Portainer (stop_stack): {response.json()['message']}")
                return False

            return False
        except Exception as e:
            UtilsLog.error(f'Portainer (stop_stack): {e}')
            return False
