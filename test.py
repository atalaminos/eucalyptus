import requests


class PortainerManager:
    def __init__(self, portainer_url, username, password, verify_ssl=False):
        """
        Inicializa el gestor de Portainer

        Args:
            portainer_url: URL de Portainer (ej: https://portainer.example.com:9443)
            username: Usuario de Portainer
            password: Contraseña
            verify_ssl: Si False, ignora errores de certificado SSL (para certificados autofirmados)
        """
        self.base_url = portainer_url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.token = None

        # Deshabilitar warnings de SSL si no verificamos
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.authenticate(username, password)

    def authenticate(self, username, password):
        """Autentica y obtiene el token JWT"""
        url = f"{self.base_url}/api/auth"
        payload = {"username": username, "password": password}

        response = requests.post(url, json=payload, verify=self.verify_ssl)
        if response.status_code == 200:
            self.token = response.json()['jwt']
            print("✓ Autenticación exitosa")
        else:
            raise Exception(f"Error de autenticación: {response.text}")

    def get_headers(self):
        """Retorna los headers con el token de autenticación"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_endpoints(self):
        """Obtiene la lista de endpoints (ambientes Docker)"""
        url = f"{self.base_url}/api/endpoints"
        response = requests.get(url, headers=self.get_headers(), verify=self.verify_ssl)
        return response.json() if response.status_code == 200 else []

    def get_containers(self, endpoint_id=1):
        """Obtiene todos los contenedores de un endpoint"""
        url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/json?all=true"
        response = requests.get(url, headers=self.get_headers(), verify=self.verify_ssl)
        return response.json() if response.status_code == 200 else []

    def get_image_info(self, endpoint_id, image_name):
        """Obtiene información de una imagen desde Docker Hub"""
        url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/images/{image_name}/json"
        response = requests.get(url, headers=self.get_headers(), verify=self.verify_ssl)
        print(response.json())
        return response.json() if response.status_code == 200 else None

    def get_local_image(self, endpoint_id, image_id):
        """Obtiene información de una imagen local por su ID"""
        # Limpiar el ID si tiene el prefijo sha256:
        clean_id = image_id.replace('sha256:', '')
        url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/images/{clean_id}/json"
        response = requests.get(url, headers=self.get_headers(), verify=self.verify_ssl)
        return response.json() if response.status_code == 200 else None

    def check_registry_image(self, endpoint_id, image_name):
        """Verifica la versión más reciente de una imagen en el registro"""
        try:
            # Hacer pull de la imagen (esto actualiza los metadatos sin descargar si ya existe)
            url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/images/create"
            params = {"fromImage": image_name}

            # Solo obtener los metadatos
            response = requests.post(url, headers=self.get_headers(), params=params, stream=True,
                                     verify=self.verify_ssl)

            print(response.status_code)
            if response.status_code == 200:
                # Ahora obtener la info de la imagen recién "pulled"
                return self.get_image_info(endpoint_id, image_name)

            return None
        except Exception as e:
            print(f"      Error consultando registro: {str(e)}")
            return None

    def check_for_updates(self, endpoint_id=1):
        """Verifica qué contenedores tienen actualizaciones disponibles"""
        containers = self.get_containers(endpoint_id)
        updates_available = []

        print(f"\n{'=' * 80}")
        print(f"Revisando {len(containers)} contenedores...")
        print(f"{'=' * 80}\n")

        for container in containers:

            if 'lazylibrarian' not in container['Names'][0]:
                continue

            name = container['Names'][0].lstrip('/')
            image = container['Image']
            container_id = container['Id'][:12]
            state = container['State']
            image_id = container['ImageID']

            print(f"📦 {name}")
            print(f"   Imagen actual: {image}")
            print(f"   Estado: {state}")
            print(f"   ID Contenedor: {container_id}")
            print(f"   ID Imagen: {image_id[:19]}...")

            # Obtener información de la imagen local
            try:
                local_image_info = self.get_local_image(endpoint_id, image_id)
                if not local_image_info:
                    print(f"   ⚠️  No se pudo obtener info de imagen local")
                    continue

                local_image_id = local_image_info['Id']
                created_local = local_image_info.get('Created', '')

                # Intentar hacer pull de la imagen para comparar
                # Primero obtenemos el digest de la imagen actual
                print(f"   🔍 Verificando actualizaciones en el registro...")

                # Hacer pull sin realmente descargar (usando inspect en el registry)
                registry_image_info = self.check_registry_image(endpoint_id, image)
                print(registry_image_info)
                # if registry_image_info:
                #     registry_image_id = registry_image_info.get('Id', '')
                #
                #     # Comparar IDs de imagen
                #     if local_image_id != registry_image_id:
                #         print(f"   🆕 ¡ACTUALIZACIÓN DISPONIBLE!")
                #         print(f"   Local:    {local_image_id[:19]}...")
                #         print(f"   Registry: {registry_image_id[:19]}...")
                #         has_update = True
                #     else:
                #         print(f"   ✓ Imagen actualizada (sin cambios)")
                #         has_update = False
                # else:
                #     print(f"   ⚠️  No se pudo verificar el registro")
                #     has_update = None
                #
                # updates_available.append({
                #     'id': container['Id'],
                #     'name': name,
                #     'image': image,
                #     'state': state,
                #     'has_update': has_update,
                #     'local_image_id': local_image_id,
                #     'registry_image_id': registry_image_info.get('Id', '') if registry_image_info else None
                # })

            except Exception as e:
                print(f"   ❌ Error verificando: {str(e)}")
                updates_available.append({
                    'id': container['Id'],
                    'name': name,
                    'image': image,
                    'state': state,
                    'has_update': None,
                    'error': str(e)
                })

            print()

        return updates_available

    def pull_image(self, endpoint_id, image_name):
        """Descarga la última versión de una imagen"""
        url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/images/create"
        params = {"fromImage": image_name}

        print(f"⬇️  Descargando imagen: {image_name}")
        response = requests.post(url, headers=self.get_headers(), params=params, verify=self.verify_ssl)
        return response.status_code == 200

    def recreate_container(self, endpoint_id, container_id):
        """Recrea un contenedor con la nueva imagen"""
        # 1. Obtener configuración del contenedor
        url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/json"
        response = requests.get(url, headers=self.get_headers(), verify=self.verify_ssl)

        if response.status_code != 200:
            return False

        container_config = response.json()

        # 2. Detener el contenedor
        stop_url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/stop"
        requests.post(stop_url, headers=self.get_headers(), verify=self.verify_ssl)
        print(f"   ⏸️  Contenedor detenido")

        # 3. Eliminar el contenedor
        delete_url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}"
        requests.delete(delete_url, headers=self.get_headers(), verify=self.verify_ssl)
        print(f"   🗑️  Contenedor eliminado")

        # 4. Crear nuevo contenedor con la misma configuración
        create_url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/create"

        # Preparar configuración para el nuevo contenedor
        new_config = {
            "Image": container_config['Config']['Image'],
            "Env": container_config['Config']['Env'],
            "Cmd": container_config['Config']['Cmd'],
            "ExposedPorts": container_config['Config']['ExposedPorts'],
            "HostConfig": container_config['HostConfig'],
            "name": container_config['Name'].lstrip('/')
        }

        response = requests.post(create_url, headers=self.get_headers(), json=new_config, verify=self.verify_ssl)

        if response.status_code not in [200, 201]:
            print(f"   ❌ Error creando contenedor: {response.text}")
            return False

        new_container_id = response.json()['Id']

        # 5. Iniciar el nuevo contenedor
        start_url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/{new_container_id}/start"
        requests.post(start_url, headers=self.get_headers(), verify=self.verify_ssl)
        print(f"   ▶️  Nuevo contenedor iniciado")

        return True

    def update_container(self, endpoint_id, container_id, image_name):
        """Actualiza un contenedor completo"""
        print(f"\n{'=' * 80}")
        print(f"🔄 Actualizando contenedor...")
        print(f"{'=' * 80}\n")

        # 1. Descargar nueva imagen
        if not self.pull_image(endpoint_id, image_name):
            print("❌ Error descargando imagen")
            return False

        print("✓ Imagen descargada\n")

        # 2. Recrear contenedor
        if self.recreate_container(endpoint_id, container_id):
            print("\n✅ Contenedor actualizado exitosamente")
            return True
        else:
            print("\n❌ Error actualizando contenedor")
            return False


# Ejemplo de uso
if __name__ == "__main__":
    # Configuración
    PORTAINER_URL = "https://portainer-dietpi-9443.wg.es"  # Tu URL con HTTPS
    USERNAME = "admin"
    PASSWORD = "admin12A!"
    VERIFY_SSL = False  # Cambiar a True si tienes un certificado válido

    try:
        # Inicializar gestor
        manager = PortainerManager(PORTAINER_URL, USERNAME, PASSWORD, verify_ssl=VERIFY_SSL)

        # Obtener endpoints
        endpoints = manager.get_endpoints()
        print(f"\n📍 Endpoints disponibles: {len(endpoints)}")
        for ep in endpoints:
            print(f"   - {ep['Name']} (ID: {ep['Id']})")

        # Revisar contenedores (usa el ID del endpoint, normalmente 1)
        ENDPOINT_ID = 2
        containers = manager.check_for_updates(ENDPOINT_ID)

        # Mostrar resumen
        print("\n" + "=" * 80)
        print("📊 RESUMEN DE ACTUALIZACIONES")
        print("=" * 80)

        with_updates = [c for c in containers if c.get('has_update') == True]
        up_to_date = [c for c in containers if c.get('has_update') == False]
        unknown = [c for c in containers if c.get('has_update') is None]

        print(f"✅ Actualizados: {len(up_to_date)}")
        print(f"🆕 Con actualizaciones disponibles: {len(with_updates)}")
        print(f"⚠️  No verificados: {len(unknown)}")

        if with_updates:
            print(f"\n📋 Contenedores con actualizaciones:")
            for c in with_updates:
                print(f"   • {c['name']} ({c['image']})")

        # Ejemplo: actualizar un contenedor específico
        if with_updates:
            print("\n" + "=" * 80)
            print("Para actualizar un contenedor, descomenta el código de ejemplo:")
            print("=" * 80)

            # Descomentar para actualizar el primer contenedor con updates:
            # container = with_updates[0]
            # manager.update_container(
            #     ENDPOINT_ID,
            #     container['id'],
            #     container['image']
            # )

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")