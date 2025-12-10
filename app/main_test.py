import asyncio

from dotenv import load_dotenv

from modules.helpers.conf import Conf
from modules.helpers.rclone_api import RcloneApi
from utils.utils_telegram import UtilsTelegram

load_dotenv()

conf = Conf()
# print(conf.get('DNSSERVER_ENDPOINT'))
# print(conf.set('DNSSERVER_ENDPOINT', 'a'))
# print(conf.get('DNSSERVER_ENDPOINT'))
# print(conf.clear())
# print(conf.get('DNSSERVER_ENDPOINT'))

# dnsserver_api = DnsserverApi()
# print(dnsserver_api.login())
# print(dnsserver_api.add_record('prueba.wg.es'))
# print(dnsserver_api.delete_record('prueba.wg.es'))
# print(dnsserver_api.get_records('wg.es'))

# portainer = PortainerApi()
# print(portainer.login())
# print(portainer.download_latest_image('redis'))
# print(portainer.get_containers())
# print(portainer.get_image_info_by_name('redis'))
# print(portainer.get_image_info_by_id('sha256:017b1c12abf9d52fe40dda80a195107ea2c566a0035b59ffcc67af8b4c32c736'))
# print(portainer.get_stacks())
# print(portainer.get_stack_with_containers('changedetection1-1'))
# print(portainer.get_stacks_with_containers())
# print(portainer.get_images())
# print(portainer.get_volumes())

# UtilsTelegram.enviar_mensaje("as")

rclone = RcloneApi()
# print(rclone.config_show())
# print(rclone.config_create('mega1', 'mega_esperando4', 'esperando4@gmail.com', 'xxx', '4545332))
# print(rclone.ls('mega_esperando4'))
# print(rclone.move('mega_esperando4', '../.gitignore',  '/'))

# Archivo
# print(rclone.copy('mega_esperando4-crypt', '../test.py', '/'))
# print(rclone.download('mega_esperando4-crypt', '/test.py', 'd:/incoming/test.py'))

# Directorios
# print(rclone.copy('mega_esperando4-crypt', '../extern', '/'))
# print(rclone.download('mega_esperando4-crypt', '/extern', 'd:/incoming/extern'))

# print(rclone.copy('mega_esperando4-crypt', '../docker_data/bookstack1-1', '/prueba'))
# print(rclone.download('mega_esperando4-crypt', '/prueba/bookstack1-1', 'd:/incoming/bookstack1-1'))

# print(rclone.ls('mega'))
# print(rclone.mkdir('mega_esperando4', 'prueba'))
# print(rclone.purge('mega_esperando4', 'prueba'))
# print(rclone.copy('../app', 'mega_esperando4', '/app'))
