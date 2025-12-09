import json
import os
import re
import shutil
import subprocess
import tarfile
from pathlib import Path
import tempfile


import zstandard as zstd

from modules.helpers.conf import Conf

SUFFIX_CRYPT = '-crypt'


class RcloneApi:
    def __init__(self):
        self.conf = Conf()
        self.remotes: dict = self.conf.get('RCLONE_REMOTES')
        if os.name == 'nt':
            self.executable = '../extern/rclone/rclone.exe'
        else:
            self.executable = 'rclone'

    def config_create(self, name: str, remote_type: str, username: str, password: str):
        try:
            # Crear remoto base
            result_base = subprocess.run(
                [self.executable, 'config', 'create', name, remote_type,
                 f'user={username}', f'pass={password}'],
                capture_output=True,
                text=True,
                check=True
            )

            crypt_name = f'{name}{SUFFIX_CRYPT}'
            crypt_remote_path = self.conf.get('RCLONE_PATH')
            crypt_password1 = self.conf.get('RCLONE_PASSWORD1')
            crypt_password2 = self.conf.get('RCLONE_PASSWORD2')

            # Ofuscar las contraseñas con rclone obscure
            obscured_pass1 = subprocess.run(
                [self.executable, 'obscure', crypt_password1],
                capture_output=True, text=True, check=True
            ).stdout.strip()

            obscured_pass2 = ''
            if crypt_password2:
                obscured_pass2 = subprocess.run(
                    [self.executable, 'obscure', crypt_password2],
                    capture_output=True, text=True, check=True
                ).stdout.strip()

            # Crear remoto crypt
            result_crypt = subprocess.run(
                [self.executable, 'config', 'create', crypt_name, 'crypt',
                 f'remote={name}:{crypt_remote_path}',
                 f'password={obscured_pass1}',
                 f'password2={obscured_pass2}',
                 'filename_encryption=standard'],
                capture_output=True,
                text=True,
                check=True
            )
            return result_base.stdout + result_crypt.stdout

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"config_create - Error ejecutando rclone: {e.stderr.strip()}") from e

    def config_delete(self, name: str):
        try:
            result1 = subprocess.run(
                [self.executable, 'config', 'delete', name],
                capture_output=True,
                text=True,
                check=True
            )

            result2 = subprocess.run(
                [self.executable, 'config', 'delete', f'{name}{SUFFIX_CRYPT}'],
                capture_output=True,
                text=True,
                check=True
            )
            return result1.stdout + result2.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"config_create - Error ejecutando rclone: {e.stderr.strip()}") from e
        except json.JSONDecodeError:
            raise RuntimeError(f"config_create - Error decodificando la salida de rclone: {result1.stdout.strip() + result2.stdout.strip()}")

    def config_show(self):
        try:
            result = subprocess.run(
                [self.executable, 'config', 'show'],
                capture_output=True,
                text=True,
                check=True
            )
            results = {}
            current = None

            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                m = re.match(r'\[(.+?)\]', line)
                if m:
                    current = m.group(1)
                    results[current] = {}
                    continue
                if '=' in line and current:
                    k, v = line.split('=', 1)
                    results[current][k.strip()] = v.strip()

            return results

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"config_show - Error ejecutando rclone: {e.stderr.strip()}") from e
        except json.JSONDecodeError:
            raise RuntimeError(f"config_show - Error decodificando la salida de rclone: {result.stdout.strip()}")

    def config_set(self):
        remotes_configured = self.config_show()

        # Cuál hay que añadir
        for remote in self.remotes:
            if remote not in list(remotes_configured.keys()):
                self.config_create(remote['name'], remote['type'], remote['username'], remote['password'])

        # Cuál hay que borrar
        for remote_name in remotes_configured:
            if not any(remote_name == r['name'] or remote_name == f"{r['name']}{SUFFIX_CRYPT}" for r in self.remotes):
                self.config_delete(remote_name)

    def copy(self, remote: str, file: str, path: str, compress=True):
        file_to_upload = file
        compressed_file = None
        is_directory = Path(file).is_dir()

        try:
            if compress:
                base_name = Path(file).name
                compressed_file = f"{base_name}.zst"

                cctx = zstd.ZstdCompressor(level=22, threads=-1)
                
                if is_directory:
                    # Para directorios, comprimimos todo el contenido con tar
                    tar_temp = f"{base_name}.tar"
                    with tarfile.open(tar_temp, "w") as tar:
                        tar.add(file, arcname=base_name)
                    
                    with open(tar_temp, 'rb') as f_in, open(compressed_file, 'wb') as f_out:
                        cctx.copy_stream(f_in, f_out)
                    os.remove(tar_temp)
                else:
                    # Para archivos, comprimimos directamente
                    with open(file, 'rb') as f_in, open(compressed_file, 'wb') as f_out:
                        cctx.copy_stream(f_in, f_out)

                file_to_upload = compressed_file

            result = subprocess.run(
                [self.executable, 'copy', file_to_upload, f"{remote}:{path}"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"copy Error ejecutando rclone: {e.stderr.strip()}") from e
        finally:
            if compressed_file and Path(compressed_file).exists():
                Path(compressed_file).unlink()

    def download(self, remote: str, remote_path: str, local_path: str, decompress=True):

        local_path_original = str(local_path)

        try:

            if decompress:
                local_path = f"{Path(remote_path).stem}.zst"
                remote_path = f"{Path(remote_path).stem}.zst"

            # Descarga usando rclone al directorio destino, pero de forma temporal
            result = subprocess.run(
                [self.executable, 'copy', f"{remote}:{remote_path}", Path(local_path).parent],
                capture_output=True,
                text=True,
                check=True
            )

            # Si es necesario, descomprimir
            if decompress:
                with open(local_path, "rb") as f_in:
                    dctx = zstd.ZstdDecompressor()
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.tar') as tmp_tar:
                        dctx.copy_stream(f_in, tmp_tar)
                        tmp_tar_path = tmp_tar.name
                
                # Extraer el tar al path especificado
                os.makedirs(local_path_original, exist_ok=True)
                with tarfile.open(tmp_tar_path, "r") as tar:
                    # Extraer solamente el contenido del directorio (saltando el directorio padre)
                    members = tar.getmembers()
                    for member in members:
                        # Remover el primer componente del path (nombre del directorio)
                        parts = Path(member.name).parts
                        if len(parts) > 1:
                            member.name = str(Path(*parts[1:]))
                        else:
                            continue
                        tar.extract(member, path=local_path_original)
                
                os.remove(tmp_tar_path)
                os.remove(local_path)

            return result.stdout

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"download Error ejecutando rclone: {e.stderr.strip()}") from e

    def ls(self, remote: str):
        try:
            result = subprocess.run(
                [self.executable, 'ls', f'{remote}:/'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ls - Error ejecutando rclone: {e.stderr.strip()}") from e
        except json.JSONDecodeError:
            raise RuntimeError(f"ls - Error decodificando la salida de rclone: {result.stdout.strip()}")

    def mkdir(self, remote: str, path: str):
        try:
            result = subprocess.run(
                [self.executable, 'mkdir', f'{remote}:{path}'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"mkdir Error ejecutando rclone: {e.stderr.strip()}") from e
        except json.JSONDecodeError:
            raise RuntimeError(f"mkdir - Error decodificando la salida de rclone: {result.stdout.strip()}")

    def move(self, remote: str, file: str, path: str):
        try:
            result = subprocess.run(
                [self.executable, 'move', file, f'{remote}/{path}'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"move - Error ejecutando rclone: {e.stderr.strip()}") from e
        except json.JSONDecodeError:
            raise RuntimeError(f"move - Error decodificando la salida de rclone: {result.stdout.strip()}")

    def purge(self, remote: str, path: str):
        try:
            result = subprocess.run(
                [self.executable, 'purge', f'{remote}:{path}'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"purge Error ejecutando rclone: {e.stderr.strip()}") from e
        except json.JSONDecodeError:
            raise RuntimeError(f"purge - Error decodificando la salida de rclone: {result.stdout.strip()}")
