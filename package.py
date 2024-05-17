#!/usr/bin/env python3
import argparse
import base64
import logging
import os
import platform
import shutil
import stat
import subprocess  # noqa: S404
import sys
import urllib.request
from collections.abc import Callable, Generator
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal

from setuptools_scm import get_version

from packaging import version

rotki_version = get_version()

pyinstaller_version = os.environ.get('PYINSTALLER_VERSION', '6.3.0')
BACKEND_PREFIX = 'rotki-core'
SUPPORTED_ARCHS = [
    'AMD64',  # Windows
    'x86_64',
    'aarch64',
    'arm64',
]
SUPPORTED_OSES = [
    'Darwin',
    'Windows',
    'Linux',
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
)
logger = logging.getLogger('package')

MAC_CERTIFICATE = 'CERTIFICATE_OSX_APPLICATION'
WIN_CERTIFICATE = 'CERTIFICATE_WIN_APPLICATION'
CERTIFICATE_KEY = 'CSC_KEY_PASSWORD'
APPLE_ID = 'APPLEID'
APPLE_ID_PASS = 'APPLEIDPASS'
X64_APPL_RUST_TARGET = 'x86_64-apple-darwin'
ARM_APPL_RUST_TARGET = 'aarch64-apple-darwin'


def log_group(name: str) -> Callable:
    def start_group(group_name: str) -> None:
        if os.environ.get('CI'):
            subprocess.call(f'echo ::group::"{group_name}"', shell=True)
        else:
            logger.info(f'\n\n-----{group_name}-----\n\n')

    def end_group() -> None:
        if os.environ.get('CI'):
            subprocess.call('echo ::endgroup::', shell=True)
        else:
            logger.info('\n\n-----------------\n\n')

    def decorate(fn: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any | None) -> None:
            start_group(name)
            fn(*args, **kwargs)
            end_group()

        return wrapper
    return decorate


class Environment:
    def __init__(self) -> None:
        self.arch = platform.machine()
        self.os = platform.system()
        self.target_arch = os.environ.get('MACOS_BUILD_ARCH', self.arch)

        if self.is_mac():
            os.environ.setdefault('ONEFILE', '0')

        self.rotki_version = rotki_version
        if os.environ.get('ROTKI_VERSION') is None:
            os.environ.setdefault('ROTKI_VERSION', self.rotki_version)

        self.__certificate_mac = os.environ.get(MAC_CERTIFICATE)
        self.__certificate_win = os.environ.get(WIN_CERTIFICATE)
        self.__csc_password = os.environ.get(CERTIFICATE_KEY)
        self.__appleid = os.environ.get(APPLE_ID)
        self.__appleidpass = os.environ.get(APPLE_ID_PASS)

        os.environ.pop(MAC_CERTIFICATE, None)
        os.environ.pop(WIN_CERTIFICATE, None)
        os.environ.pop(CERTIFICATE_KEY, None)
        os.environ.pop(APPLE_ID, None)
        os.environ.pop(APPLE_ID_PASS, None)

    def macos_sign_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.__csc_password is not None:
            env.setdefault(CERTIFICATE_KEY, self.__csc_password)
        if self.__appleid is not None:
            env.setdefault(APPLE_ID, self.__appleid)
        if self.__appleidpass is not None:
            env.setdefault(APPLE_ID_PASS, self.__appleidpass)
        return env

    def macos_sign_vars(self) -> dict[str, str | None]:
        return {
            'certificate': self.__certificate_mac,
            'key': self.__csc_password,
            'appleid': self.__appleid,
            'appleidpass': self.__appleidpass,
        }

    def win_sign_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.__csc_password is not None:
            env.setdefault(CERTIFICATE_KEY, self.__csc_password)
        return env

    def win_sign_vars(self) -> dict[str, str | None]:
        return {
            'certificate': self.__certificate_win,
            'key': self.__csc_password,
        }

    @staticmethod
    def sanity_check() -> None:
        """
        Sanity check that exits if any os the secret environment variables is set when called.
        """
        mac_cert = os.environ.get(MAC_CERTIFICATE)
        win_cert = os.environ.get(WIN_CERTIFICATE)
        key_pass = os.environ.get(CERTIFICATE_KEY)
        appleid = os.environ.get(APPLE_ID)
        appleidpass = os.environ.get(APPLE_ID_PASS)

        sign_vars = [mac_cert, win_cert, key_pass, appleid, appleidpass]

        if any(sign_vars):
            logger.error('at least one of the secrets was set in the environment')
            sys.exit(1)

    @staticmethod
    def check_repo() -> None:
        output = subprocess.check_output(
            'git branch --show-current',
            encoding='utf8',
            shell=True,
        ).strip()

        if output != 'master':
            logger.info(f'Current branch is {output}, skipping check')
            return

        unmerged_commits = subprocess.check_output(
            'git rev-list HEAD..bugfixes --no-merges | wc -l | xargs echo -n',
            encoding='utf8',
            shell=True,
        ).strip()

        if unmerged_commits != '0':
            logger.error(
                f'Found {unmerged_commits} in bugfixes that have not been merged for release',
            )
            sys.exit(1)
        logger.info('branch is up to date with bugfixes')

    def check_environment(self) -> None:
        if self.arch not in SUPPORTED_ARCHS:
            logger.error(
                f'{self.arch} is not supported, packaging only supports {SUPPORTED_ARCHS}',
            )
            sys.exit(1)

        if self.os not in SUPPORTED_OSES:
            logger.error(
                f'{platform.system()} is not supported, packaging only supports {SUPPORTED_OSES}',
            )
            sys.exit(1)

        if not self.is_ci() and not os.environ.get('VIRTUAL_ENV'):
            logger.error('The script should not run outside a virtual environment if not on CI')
            sys.exit(1)

        self.check_repo()

    def is_mac(self) -> bool:
        return self.os == 'Darwin'

    def is_linux(self) -> bool:
        return self.os == 'Linux'

    def is_windows(self) -> bool:
        return self.os == 'Windows'

    def is_mac_runner(self) -> bool:
        return self.is_mac() and self.is_ci()

    def is_universal2(self) -> bool:
        return self.is_mac_runner() or os.environ.get('MACOS_BUILD_ARCH') == 'universal2'

    def is_x86_64(self) -> bool:
        return self.arch in {'x86_64', 'AMD64'}

    def backend_suffix(self) -> str:
        """
        Provides the os specific backend binary suffix.

        In Linux and macOS the executables/binaries have no extension but in windows
        they have the .exe extension. Since the suffix is used to match filenames
        for windows the suffix also contains the extension to remove the need to
        check again for windows and attach the extension in the method consumers.

        :returns: The backends os specific filename suffix.
        """
        if self.is_mac():
            return 'macos'
        if self.is_linux():
            return 'linux'
        if self.is_windows():
            return 'windows.exe'
        raise ValueError(f'Invalid os {self.os}')

    @staticmethod
    def mac_electron_env_set() -> bool:
        return os.environ.get('MACOS_ELECTRON_ARCH') is not None

    def get_frontend_env(self) -> dict[str, str]:
        if os.environ.get('GH_TOKEN'):
            logger.info('GH_TOKEN WAS SET')
        else:
            logger.info('NO GH_TOKEN SET')
        env = os.environ.copy()
        if self.is_mac() and not self.mac_electron_env_set() and not self.is_ci():
            arch = 'x64' if self.is_x86_64() else 'arm64'

            env.setdefault('MACOS_ELECTRON_ARCH', arch)
        return env

    @staticmethod
    def is_ci() -> bool:
        return os.environ.get('CI') is not None


class Checksum:
    @staticmethod
    def generate(env: Environment, path: Path) -> Path:
        checksum_filename = f'{path.name}.sha512'
        cmd = None
        if env.is_mac():
            cmd = f'shasum -a 512 {path.name} > {checksum_filename}'
        elif env.is_linux():
            cmd = f'sha512sum {path.name} > {checksum_filename}'
        elif env.is_windows():
            cmd = f'powershell.exe -command "Get-FileHash {path.name} -Algorithm SHA512 | Select-Object Hash | foreach {{$_.Hash}} | Out-File -FilePath {checksum_filename}"'  # noqa: E501
        else:
            logger.error('unsupported system')
            sys.exit(1)

        ret_code = subprocess.call(cmd, cwd=path.parent, shell=True)
        if ret_code != 0:
            logger.error(f'could not generate sha512 sum for {path}')
            sys.exit(1)
        return path.parent / checksum_filename


class Storage:
    def __init__(self) -> None:
        self.working_directory = Path.cwd()
        self.dist_directory = self.working_directory / 'dist'
        self.build_directory = self.working_directory / 'build'
        self.wheel_directory = self.build_directory / 'wheels'
        self.temporary_directory = self.build_directory / 'temp'
        self.backend_directory = self.build_directory / 'backend'
        self.colibri_directory = self.build_directory / 'colibri'
        self.build_directory.mkdir(parents=True, exist_ok=True)

    def prepare_backend(self) -> None:
        if self.backend_directory.exists():
            shutil.rmtree(self.backend_directory)
        self.backend_directory.mkdir(parents=True, exist_ok=True)

    def prepare_temp(self) -> None:
        self.temporary_directory.mkdir(exist_ok=True, parents=True)

    def move_to_dist(self, file: Path) -> None:
        self.dist_directory.mkdir(exist_ok=True)
        logger.info(f'moving {file.name} to {self.dist_directory}')
        shutil.move(src=file, dst=self.dist_directory)

    def check_backend(self) -> None:
        backend = self.backend_directory
        if not backend.exists() or not any(backend.iterdir()):
            logger.error(f'{backend} was missing or empty')
            sys.exit(1)

    def copy_to_dist(self, src: Path, sub_dir: str | None = None) -> None:
        self.dist_directory.mkdir(exist_ok=True)

        dst = self.dist_directory
        if sub_dir is not None:
            dst /= sub_dir

        logger.info(f'copying {src.name} to {dst}')

        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy(src=src, dst=dst)

    def clean(self) -> None:
        shutil.rmtree(self.build_directory)


class WindowsPackaging:
    def __init__(self, storage: Storage, env: Environment) -> None:
        self.__storage = storage
        self.__env = env
        self.__p12 = Path('')

    @log_group('miniupnpc windows')
    def setup_miniupnpc(self) -> None:
        """
        Downloads miniupnpc and extracts the dll in the virtual environment.
        """
        python_dir = Path(
            subprocess.check_output(
                'python -c "import os, sys; print(os.path.dirname(sys.executable))"',
                encoding='utf8',
                shell=True,
            ).strip(),
        )

        if python_dir.name != 'Scripts':
            python_dir /= 'Scripts'

        dll_filename = 'miniupnpc.dll'
        dll_path = python_dir / dll_filename
        if dll_path.exists():
            logger.info(f'miniupnpc.dll is already installed in {python_dir}')
            return

        build_dir = self.__storage.build_directory
        os.chdir(build_dir)

        dll_file = build_dir / dll_filename

        url = f'https://github.com/rotki/rotki-build/raw/main/miniupnpc/dll/2.2.6/{dll_filename}'
        urllib.request.urlretrieve(url, dll_file)  # noqa: S310

        logger.info(f'moving {dll_file} to {python_dir}')

        shutil.move(
            src=dll_file,
            dst=python_dir,
        )

    @log_group('certificates')
    def import_signing_certificates(self) -> bool:
        """
        Imports the signing certificates from the environment variables
        and prepares for signing.

        The function will bail (exit 1) when the certificate is set but
        no key has been passed in the configuration.

        :return: True when the certificate and key are properly setup,
        False when the certificate is not configured.
        """
        sign_vars = self.__env.win_sign_vars()
        certificate = sign_vars.get('certificate')
        csc_password = sign_vars.get('key')

        if os.environ.get('WIN_CSC_LINK') is not None and csc_password is not None:
            logger.info('WIN_CSC_LINK already set skipping')
            return True

        if certificate is None:
            logger.info(f'{WIN_CERTIFICATE} is not set skipping signing')
            return False

        if csc_password is None:
            logger.error(f'Missing {CERTIFICATE_KEY}')
            sys.exit(1)

        logger.info('preparing to sign windows installer')
        with NamedTemporaryFile(delete=False, suffix='.p12') as p12:
            self.__p12 = Path(p12.name)
            os.environ.setdefault('WIN_CSC_LINK', str(self.__p12))
            certificate_data = base64.b64decode(certificate)
            p12.write(certificate_data)

        return True

    def cleanup_certificate(self) -> None:
        self.__p12.unlink(missing_ok=True)


class MacPackaging:
    def __init__(self, storage: Storage, environment: Environment) -> None:
        self.__storage = storage
        self.__environment = environment
        self.__default_keychain: str | None = None
        self.__keychain = 'rotki-build.keychain'
        self.__p12 = Path('/tmp/certificate.p12')  # noqa: S108

    @staticmethod
    def unpack_wheels(
            package_version: str,
            plt: Literal['macosx_10_9_x86_64', 'macosx_11_0_arm64'],
            directory: Path,
    ) -> None:
        logger.info(f'preparing to download {package_version} wheel for {plt}')
        directory.mkdir(exist_ok=True)
        os.chdir(directory)
        subprocess.call(
            f'pip download {package_version} --platform {plt} --only-binary=:all:',
            shell=True,
        )
        pkg_arch = 'x86_64' if plt.find('x86_64') >= 0 else 'arm64'
        for file in directory.iterdir():
            logger.info(f'checking if {file} package is {pkg_arch}')
            if file.name.find(pkg_arch) >= 0:
                logger.info(f'unpacking wheel {file}')
                subprocess.call(f'wheel unpack {file}', shell=True)

            file.unlink()

    @staticmethod
    def macos_link_archs(source: Path, destination: Path) -> None:
        """
        Uses lipo to create a dual architecture library for macOS by merging a x86_64
        and an arm64 library.
        The order can be any but keep in mind that destination will become the dual
        architecture one.

        :param source: One of the two libraries that will be merged with lipo.
        :param destination: The library that will become the dual architecture one.
        """
        logger.info(f'creating fat binary {source} <-> {destination}')
        ret_code = subprocess.call(
            f'lipo -create -output {destination} {source} {destination}',
            shell=True,
        )

        if ret_code != 0:
            logger.error(f'failed to create a fat binary {source} {destination}')
            sys.exit(1)

        archs = subprocess.check_output(f'lipo -archs {destination}', encoding='utf-8', shell=True)

        if archs.strip() != 'x86_64 arm64':
            logger.error(f'{destination} was not a fat binary, only has {archs}')
            sys.exit(1)

    @staticmethod
    def modify_wheel_metadata(wheel_metadata: Path) -> None:
        """
        Modifies the tag in the wheel metadata file from x86_64 to universal2 so
        that the repackaged wheel has the proper tag.

        :param wheel_metadata: Path to the wheel metadata file
        """
        with open(wheel_metadata, encoding='utf8') as file:
            data = file.readlines()
            for (index, line) in enumerate(data):
                if not line.startswith('Tag'):
                    continue
                data[index] = line.replace('x86_64', 'universal2')

        with open(wheel_metadata, 'w', encoding='utf8') as file:
            file.writelines(data)

    def __download_patched_pip(self) -> Path:
        """
        Downloads the patched pip version needed to create a universal2 virtual environment.
        :return:
        """
        pip_wheel = 'pip-22.1.2-py3-none-any.whl'
        temporary_directory = self.__storage.temporary_directory
        temporary_directory.mkdir(exist_ok=True)
        wheel_file = temporary_directory / pip_wheel
        urllib.request.urlretrieve(  # noqa: S310
            url=f'https://github.com/rotki/rotki-build/raw/main/{pip_wheel}',
            filename=wheel_file,
        )
        return Path(wheel_file)

    def __get_versions(self, packages: list[str]) -> dict[str, str]:
        """
        Gets the versions of specified packages from requirements.txt
        and requirements_crossbuild.txt.

        :param packages: A list of package names for which we need versions from
        the requirements.txt
        :returns: A Dict where the key is the package and the value is the package version
        """
        package_versions: dict[str, str] = {}
        for requirement_file_name in ('requirements.txt', 'requirements_crossbuild.txt'):
            requirements = self.__storage.working_directory / requirement_file_name
            with open(requirements, encoding='utf8') as fp:
                while True:
                    line = fp.readline()
                    if not line:
                        break
                    if len(line.strip()) == 0 or line.startswith('#'):
                        continue
                    requirement = line.split('#')[0]
                    req = requirement.split(';')
                    requirement = req[0]
                    if len(req) > 1 and req[1].strip() == "sys_platform == 'win32'":
                        continue

                    split_requirement = requirement.split('==')
                    package_name = split_requirement[0]
                    if package_name in packages:
                        package_version = split_requirement[1]
                        if (processed_package_name := package_name.strip()) in package_versions:
                            logger.error(
                                f'{processed_package_name} dependency appeared more than once '
                                f'while reading the file {requirements}',
                            )
                            sys.exit(1)
                        package_versions[processed_package_name] = package_version.strip()

        return package_versions

    @log_group('universal2 wheel')
    def __universal_repackage(self, package_name: str) -> None:
        """
        Creates universal2 wheels for packages.

        coincurve and cffi only provide architecture specific wheels (x86_64, arm64)
        for macOS. To create a universal2 wheel we download the architecture
        specific wheels, unpack them, then merge any native extension (*.so) using lipo.
        Next we modify the tag so that re-packed wheel is properly tagged as universal
        and we finally pack the wheel again.
        """
        storage = self.__storage
        logger.info(f'Preparing to merge {package_name} wheels')
        versions = self.__get_versions(packages=[package_name])
        build_directory = storage.build_directory
        if not build_directory.exists():
            build_directory.mkdir(parents=True)

        temp = build_directory / 'temp'
        temp.mkdir(parents=True, exist_ok=True)

        wheels_directory = build_directory / 'wheels'
        wheels_directory.mkdir(parents=True, exist_ok=True)

        x86_64 = temp / 'x86_64'
        arm64 = temp / 'arm64'

        package = f'{package_name}=={versions.get(package_name)}'
        self.unpack_wheels(package, 'macosx_10_9_x86_64', x86_64)
        self.unpack_wheels(package, 'macosx_11_0_arm64', arm64)

        for unpacked_wheel in x86_64.iterdir():
            so_libs = unpacked_wheel.glob('**/*.so')
            for so_lib in so_libs:
                arm64_solib = next(arm64.glob(f'**/{so_lib.name}'))
                self.macos_link_archs(destination=so_lib, source=arm64_solib)
            metadata = next(unpacked_wheel.glob('**/WHEEL'))
            logger.info(f'preparing to modify metadata: {metadata}')
            self.modify_wheel_metadata(metadata)
            ret_code = subprocess.call(
                f'wheel pack {unpacked_wheel} -d {wheels_directory}',
                shell=True,
            )
            if ret_code != 0:
                logger.error(f'repack of {unpacked_wheel} failed')
                sys.exit(1)

        shutil.rmtree(x86_64)
        shutil.rmtree(arm64)

    @log_group('miniupnpc universal2 wheel')
    def __build_miniupnpc_universal(self) -> None:
        """
        Builds a universal2 wheel for miniupnpc.

        Miniupnpc builds the native library libminiupnpc.a and then statically links
        the native extension against that.

        Unfortunately it is not possible to pass dual architecture flags to the compiler
        and build a universal wheel in one step. Instead, we download the package source
        and build the static library once for each architecture.

        Then we use lipo to merge the two static libraries to one dual arch library
        which is then used when we create the universal2 wheel.
        """
        logger.info('Preparing to create universal2 wheels for miniupnpc')

        self.__storage.prepare_temp()
        temp = self.__storage.temporary_directory
        build_directory = self.__storage.build_directory
        package_name = 'miniupnpc'
        versions = self.__get_versions([package_name])

        libminiupnpc_dylib = 'libminiupnpc.dylib'
        libminiupnpc_a = 'libminiupnpc.a'
        miniupnpc_version = versions.get(package_name)
        miniupnpc = f'{package_name}-{miniupnpc_version}'
        miniupnpc_archive = f'{miniupnpc}.tar.gz'
        miniupnpc_directory = build_directory / miniupnpc

        os.chdir(build_directory)
        download_result = subprocess.call(
            f'pip download {package_name}=={miniupnpc_version}',
            shell=True,
        )

        if download_result != 0:
            logger.error(f'failed to download {package_name}')
            sys.exit(1)

        extract_result = subprocess.call(f'tar -xvf {miniupnpc_archive}', shell=True)

        if extract_result != 0:
            logger.error(f'failed to extract {package_name}')
            sys.exit(1)

        os.chdir(miniupnpc_directory)

        env = os.environ.copy()
        env.setdefault('CC', 'gcc -arch x86_64')
        env.setdefault('MACOSX_DEPLOYMENT_TARGET', '10.9')
        make_x86_result = subprocess.call('make', env=env, shell=True)

        if make_x86_result != 0:
            logger.error('make failed for x86_64')
            sys.exit(1)

        shutil.move('build' / Path(libminiupnpc_dylib), temp)
        shutil.move('build' / Path(libminiupnpc_a), temp)

        make_clean_result = subprocess.call('make clean', shell=True)

        if make_clean_result != 0:
            logger.error(f'failed to clean {package_name}')
            sys.exit(1)

        env = os.environ.copy()
        env.setdefault('CC', 'gcc -arch arm64')
        env.setdefault('MACOSX_DEPLOYMENT_TARGET', '11.0')
        make_arm64_result = subprocess.call('make', env=env, shell=True)

        if make_arm64_result != 0:
            logger.error('make failed for arm64')
            sys.exit(1)

        self.macos_link_archs(
            destination='build' / Path(libminiupnpc_a),
            source=temp / libminiupnpc_a,
        )
        self.macos_link_archs(
            destination='build' / Path(libminiupnpc_dylib),
            source=temp / libminiupnpc_dylib,
        )

        wheel_build_result = subprocess.call('python setup.py bdist_wheel', shell=True)
        if wheel_build_result != 0:
            logger.error(f'failed to build {package_name} wheel')
            sys.exit(1)

        miniupnpc_dist = miniupnpc_directory / 'dist'
        wheel_file = miniupnpc_dist / f'{miniupnpc}-cp311-cp311-macosx_10_9_universal2.whl'
        wheel_directory = self.__storage.wheel_directory
        wheel_directory.mkdir(exist_ok=True)
        shutil.move(wheel_file, wheel_directory)

        shutil.rmtree(temp)

        archive_path = build_directory / miniupnpc_archive

        if archive_path.exists():
            archive_path.unlink()

        if miniupnpc_directory.exists():
            shutil.rmtree(miniupnpc_directory)

    def prepare_wheels(self) -> None:
        """
        Prepares the wheels with native extensions that require
        special treatment.
        """
        self.__build_miniupnpc_universal()
        self.__universal_repackage('coincurve')
        self.__universal_repackage('ckzg')

    def install_wheels(self, install: Callable[[str], None]) -> None:
        """
        Installs the wheels that are patched or modified.

        Note that the order of installation is important for cffi/coincurve.
        If cffi is not installed first then a version will be pulled from PyPI instead.

        :param install: The install callable that is passed externally
        """
        if self.__environment.target_arch == 'universal2':
            patched_pip = self.__download_patched_pip()
            install(f'{patched_pip} --force-reinstall')
        wheel_directory = self.__storage.wheel_directory
        os.chdir(wheel_directory)
        for wheel in sorted(wheel_directory.iterdir()):
            install(str(wheel))

        # To avoid cytoolz RuntimeError on macOS
        # "Cython required to build dev version of cytoolz."
        install('cython')

    @log_group('certificates')
    def import_signing_certificates(self) -> bool:
        """
        Imports the signing certificates from the environment variables
        and prepares the keychain for signing
        """
        sign_vars = self.__environment.macos_sign_vars()
        certificate = sign_vars.get('certificate')
        csc_password = sign_vars.get('key')

        if os.environ.get('CSC_LINK') is not None and csc_password is not None:
            logger.info('CSC_LINK already set skipping')
            return True

        if certificate is None:
            logger.info(f'{MAC_CERTIFICATE} is not set skipping signing')
            return False

        if csc_password is None:
            logger.error(f'Missing {CERTIFICATE_KEY}')
            sys.exit(1)

        logger.info('preparing to sign macOS binary')
        p12 = self.__p12
        keychain = self.__keychain
        os.environ.setdefault('CSC_LINK', str(p12))

        certificate_data = base64.b64decode(certificate)
        p12.write_bytes(certificate_data)
        self.__default_keychain = subprocess.check_output(
            'security default-keychain',
            shell=True,
            encoding='utf8',
        ).strip()

        # Create a keychain
        subprocess.call(f'security create-keychain -p actions {keychain}', shell=True)
        # Make the keychain the default so identities are found
        subprocess.call(f'security default-keychain -s {keychain}', shell=True)
        # Unlock the keychains
        subprocess.call(f'security unlock-keychain -p actions {keychain}', shell=True)
        subprocess.call(
            f'security import {p12!s} -k {keychain} -P {csc_password} -T /usr/bin/codesign;',
            shell=True,
        )
        subprocess.call(
            f'security set-key-partition-list -S apple-tool:,apple:,codesign:,productbuild: -s -k actions {keychain}',  # noqa: E501
            shell=True,
        )

        return True

    def cleanup_keychain(self) -> None:
        default_keychain = self.__default_keychain
        if default_keychain is not None:
            subprocess.call(f'security default-keychain -s {default_keychain}', shell=True)

        if self.__p12.exists():
            self.__p12.unlink(missing_ok=True)
        os.environ.pop('CSC_LINK', None)

    @log_group('signing')
    def sign(self, paths: Generator[Path, None, None]) -> None:
        """
        Signs all the contents of the directory created by PyInstaller
        with the provided signing key/identity.
        """
        if not self.import_signing_certificates():
            return

        identify = os.environ.get('IDENTITY')
        for path in paths:
            if not path.is_file():
                continue

            logger.debug(f'Preparing to sign {path}')
            sign_ret_code = subprocess.call(
                f'codesign --force --options runtime --entitlements ./packaging/entitlements.plist --sign {identify} {path} --timestamp',  # noqa: E501
                shell=True,
            )

            if sign_ret_code != 0:
                logger.error(f'could not sign file {path}')
                sys.exit(1)

            verify_ret_code = subprocess.call(f'codesign --verify {path}', shell=True)

            if verify_ret_code != 0:
                logger.error(f'signature verification failed at {path}')
                sys.exit(1)
        self.cleanup_keychain()

    @log_group('zip')
    def perform_zip(self) -> None:
        """
        Creates a zip from the directory that contains the backend, checksums it
        and moves them to the dist/ directory.
        """
        backend_directory = self.__storage.backend_directory
        os.chdir(backend_directory)
        zip_filename = f'{BACKEND_PREFIX}-{self.__environment.rotki_version}-macos.zip'
        ret_code = subprocess.call(
            f'zip -vr "{zip_filename}" {BACKEND_PREFIX}/ -x "*.DS_Store"',
            shell=True,
        )
        if ret_code != 0:
            logger.error('zip failed')
            sys.exit(1)
        zip_file = backend_directory / zip_filename
        checksum_file = Checksum.generate(self.__environment, zip_file)
        self.__storage.move_to_dist(zip_file)
        self.__storage.move_to_dist(checksum_file)


class BackendBuilder:
    def __init__(
            self,
            storage: Storage,
            env: Environment,
            mac: MacPackaging | None,
            win: WindowsPackaging | None,
    ) -> None:
        self.__mac = mac
        self.__win = win
        self.__storage = storage
        self.__env = env

    def clean(self) -> None:
        storage = self.__storage
        os.chdir(storage.working_directory)
        if not self.__env.is_windows():
            clean_result = subprocess.call('make clean', shell=True)

            if clean_result != 0:
                logger.error('failed to make clean')
                sys.exit(1)
        else:
            if storage.temporary_directory.exists():
                shutil.rmtree(storage.temporary_directory)
            if storage.backend_directory.exists():
                shutil.rmtree(storage.backend_directory)

        if storage.dist_directory.exists():
            shutil.rmtree(storage.dist_directory)

    @log_group('pip install')
    def pip_install(self, what: str, use_pep_517: bool = True) -> None:
        """
        Calls pip install using subprocess.

        :param what: anything that goes after pip install
        """
        base_command = 'pip install '
        if use_pep_517 is False:
            base_command += '--no-use-pep517 '

        ret_code = subprocess.call(
            f'{base_command} {what}',
            shell=True,
            cwd=self.__storage.working_directory,
        )
        if ret_code != 0:
            logger.error(f'could not run "pip install {what}"')
            sys.exit(1)

    def __build_pyinstaller_bootloader(self, tag_version: str) -> None:
        """
        Clones PyInstaller from source, checks out a specific version
        and builds the bootloader.

        This is required for architectures other than x86_64 that do not
        have prebuilt bootloaders.

        :param tag_version: The version of PyInstaller to check out
        """
        build_directory = self.__storage.build_directory
        build_directory.mkdir(exist_ok=True)
        os.chdir(build_directory)
        git_clone_ret_code = subprocess.call(
            'git clone https://github.com/pyinstaller/pyinstaller.git',
            shell=True,
        )
        if git_clone_ret_code != 0:
            logger.error('could not clone pyinstaller')
            sys.exit(1)

        pyinstaller_directory = build_directory / 'pyinstaller'
        os.chdir(pyinstaller_directory)

        checkout_ret_code = subprocess.call(f'git checkout v{tag_version}', shell=True)
        if checkout_ret_code != 0:
            logger.error(f'failed to checkout pyinstaller v{tag_version} tag')
            sys.exit(1)

        bootloader_directory = pyinstaller_directory / 'bootloader'
        os.chdir(bootloader_directory)
        flag = '--no-universal2' if self.__env.target_arch != 'universal2' else '--universal2'

        build_ret_code = subprocess.call(f'./waf all {flag}', shell=True)
        if build_ret_code != 0:
            logger.error(f'failed to build pyinstaller bootloader for {flag}')
            sys.exit(1)

        os.chdir(pyinstaller_directory)
        install_ret_code = subprocess.call('pip install .', shell=True)
        if install_ret_code != 0:
            logger.error('failed to install pyinstaller')
            sys.exit(1)

    def __sanity_check(self) -> None:
        os.chdir(self.__storage.working_directory)
        ret_code = subprocess.call(
            'python -c "import sys;from rotkehlchen.db.misc import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)"',  # noqa: E501
            shell=True,
        )

        # Due to https://github.com/rotki/pysqlcipher3/issues/1 verification might
        # fail in macOS machines where OpenSSL is not properly setup in the path.
        # In this case we can set the SKIP_SQLCIPHER_VERIFICATION to unblock the script
        # since the error does not affect runtime.
        if ret_code != 0 and os.environ.get('SKIP_SQLCIPHER_VERIFICATION') is None:
            logger.error('could not verify sqlcipher v4')
            sys.exit(1)

    def __move_to_dist(self) -> None:
        """
        Generates a checksum for the backend and moves it along with a copy of the backend
        to the dist/ directory. The backend file is copied instead of moved because the original
        will be needed for electron-builder.
        """
        backend_directory = self.__storage.backend_directory
        os.chdir(backend_directory)
        filename = f'{BACKEND_PREFIX}-{self.__env.rotki_version}-{self.__env.backend_suffix()}'
        file = backend_directory / filename
        checksum_file = Checksum.generate(self.__env, file)
        self.__storage.copy_to_dist(file)
        self.__storage.move_to_dist(checksum_file)

    def _move_colibri_to_dist(self) -> None:
        """Move the colibri binary to dist"""
        colibri_dir = self.__storage.colibri_directory
        self.__storage.copy_to_dist(colibri_dir / 'bin', sub_dir='colibri')

    @log_group('backend_build')
    def build(self) -> None:
        """
        Packages the backend using PyInstaller and creates the rust binary
        """
        # When packaging on macOS one of the dependencies will try to access
        # GITHUB_REF during pip install and will throw an error. For this reason
        # The variable is temporarily removed and then restored.
        github_ref = os.environ.get('GITHUB_REF')
        os.environ.pop('GITHUB_REF', None)

        self.__env.sanity_check()

        mac = self.__mac
        if mac is not None and self.__env.is_universal2():
            logger.info('Doing preparation for universal2 wheels')
            mac.prepare_wheels()
            mac.install_wheels(self.pip_install)

        win = self.__win
        if win is not None:
            win.setup_miniupnpc()

        os.chdir(self.__storage.working_directory)
        # This flag only works with the patched version of pip.
        # https://github.com/kelsos/pip/tree/patched
        os.environ.setdefault('PIP_FORCE_MACOS_UNIVERSAL2', '1')
        self.pip_install('.', use_pep_517=True)
        os.environ.pop('PIP_FORCE_MACOS_UNIVERSAL2', None)

        if github_ref is not None:
            os.environ.setdefault('GITHUB_REF', github_ref)

        self.__create_rust_binary()
        self.__install_pyinstaller()
        self.__sanity_check()
        self.__package()

        # When building for mac perfom_zip() is responsible for moving the packaged backend to dist
        if mac is not None:
            backend_directory = self.__storage.backend_directory / BACKEND_PREFIX
            mac.sign(paths=backend_directory.glob('**/*'))
            mac.perform_zip()
        else:
            self.__move_to_dist()

        self._move_colibri_to_dist()

    @staticmethod
    def __rust_add_target(target: str) -> None:
        rustup_ret_code = subprocess.call(
            f'rustup target add {target}',
            shell=True,
        )

        if rustup_ret_code != 0:
            logger.error(f'could not install target: {target}')
            sys.exit(1)

    @log_group('cargo build')
    def __create_rust_binary(self) -> None:
        if not self.__env.is_universal2():
            self.__cargo_build()
        else:
            for target in (X64_APPL_RUST_TARGET, ARM_APPL_RUST_TARGET):
                self.__rust_add_target(target=target)
                self.__cargo_build(target=target)

    def __cargo_build(self, target: str | None = None) -> None:
        colibri_directory = self.__storage.colibri_directory
        target_arg = ''

        if target is not None:
            logger.info(f'building rust binary for {target}')
            target_arg = f'--target {target}'

        build_ret_code = subprocess.call(
            f'cargo build --target-dir {colibri_directory} '
            f'--manifest-path ./colibri/Cargo.toml --release {target_arg}',
            shell=True,
        )
        if build_ret_code != 0:
            logger.error('packaging failed')
            sys.exit(1)

        binary_name = 'colibri'
        if self.__win is not None:
            binary_name = f'{binary_name}.exe'

        if target is None:
            backend_binary = colibri_directory / 'release' / binary_name
        else:
            backend_binary = colibri_directory / target / 'release' / binary_name

        if target is None:
            ret_code = subprocess.call(f'{backend_binary}', shell=True)

            if ret_code != 0:
                logger.error('colibri binary check failed')
                sys.exit(1)
        else:
            logger.info(f'skipping {backend_binary} verification because it was cross compiled')

        binary_directory = colibri_directory / 'bin'
        if self.__mac is not None:
            is_x64 = self.__env.is_x86_64()
            no_target = target is None
            if (no_target and not is_x64) or target == ARM_APPL_RUST_TARGET:
                binary_directory /= 'arm64'
            elif (no_target and is_x64) or target == X64_APPL_RUST_TARGET:
                binary_directory /= 'x64'

        binary_directory.mkdir(exist_ok=True, parents=True)
        shutil.copy(backend_binary, binary_directory / binary_name)

        if self.__mac is not None:
            self.__mac.sign(binary_directory.glob('**/*'))

    @log_group('package')
    def __package(self) -> None:
        """
        Packages the rotki backend using PyInstaller with Python optimizations.

        In Linux, Windows the method will create an one-file bundled executable.

        In macOS it will create an one-folder bundle containing an executable.
        The reason we use the one-folder approach for macOS is due to signing.
        All the bundled files have to be individually signed with a valid key
        otherwise the backend will not start and will give cryptic errors instead.
        """
        self.__storage.prepare_backend()
        backend_directory = self.__storage.backend_directory
        package_env = os.environ.copy()
        package_env.setdefault('PYTHONOPTIMIZE', '2')
        package_ret_code = subprocess.call(
            f'pyinstaller --noconfirm --clean --distpath "{backend_directory}" rotkehlchen.spec',
            shell=True,
            env=package_env,
        )
        if package_ret_code != 0:
            logger.error('packaging failed')
            sys.exit(1)
        logger.info('Check binary')
        suffix = self.__env.backend_suffix()
        backend_binary = next(backend_directory.glob(f'**/{BACKEND_PREFIX}-*-{suffix}'))
        ret_code = subprocess.call(f'{backend_binary} version', shell=True)
        if ret_code != 0:
            logger.error('backend binary check failed')
            sys.exit(1)

    @log_group('Pyinstaller')
    def __install_pyinstaller(self) -> None:
        """
        Installs PyInstaller.

        On x86_64 systems except the macOS CI runner it will install
        from pip since it already contains pre-built bootloaders for the systems.

        For other systems it will checkout from source and build the bootloader
        for the system in question.
        """
        if self.__env.is_x86_64() and not self.__env.is_mac_runner():
            self.pip_install(f'pyinstaller=={pyinstaller_version}')
        else:
            self.__build_pyinstaller_bootloader(pyinstaller_version)


class FrontendBuilder:
    def __init__(
            self,
            storage: Storage,
            env: Environment,
            mac: MacPackaging | None,
            win: WindowsPackaging | None,
    ):
        self.__storage = storage
        self.__frontend_directory = storage.working_directory / 'frontend'
        self.__env = env
        self.__mac = mac
        self.__win = win

    def __ensure_backend_executable(self) -> None:
        backend_directory = self.__storage.backend_directory
        suffix = self.__env.backend_suffix()
        backend_binary = next(backend_directory.glob(f'**/{BACKEND_PREFIX}-*-{suffix}'))
        st = os.stat(backend_binary)
        os.chmod(backend_binary, st.st_mode | stat.S_IEXEC)

    @staticmethod
    def check_pnpm_version() -> None:
        pnpm_version = version.parse(subprocess.check_output(
            'pnpm --version',
            encoding='utf-8',
            shell=True,
        ))
        required_version = version.parse('9.0.0')
        if pnpm_version < required_version:
            logger.error(f'The system pnpm version is < 9.0.0 ({pnpm_version})')
            sys.exit(1)

    @log_group('electron app build')
    def build(self) -> None:
        self.__env.sanity_check()
        self.check_pnpm_version()
        self.__storage.check_backend()
        os.chdir(self.__frontend_directory)
        frontend_env = self.__env.get_frontend_env()

        self.__restore_pnpm_dependencies()
        self.__ensure_backend_executable()

        sign_env = {}
        if self.__mac is not None:
            self.__mac.import_signing_certificates()
            sign_env = self.__env.macos_sign_env()

        if self.__win is not None:
            self.__win.import_signing_certificates()
            sign_env = self.__env.win_sign_env()

        logger.info('Calling build')
        ret_code = subprocess.call('pnpm run build', shell=True, env=frontend_env)
        if ret_code != 0:
            logger.error('build failed')
            sys.exit(1)

        package_ret_code = subprocess.call(
            'pnpm run electron:package',
            shell=True,
            env=frontend_env | sign_env,
        )
        if package_ret_code != 0:
            logger.error('package failed')
            sys.exit(1)

        app_path = self.__frontend_directory / 'app'
        frontend_build_dir = app_path / 'build'
        os.chdir(frontend_build_dir)
        for path in frontend_build_dir.iterdir():
            name = path.name
            if path.is_dir() or name in {'builder-debug.yml', 'builder-effective-config.yaml'}:
                continue

            suffixes = ['dmg', 'zip', 'exe', 'AppImage', 'tar.xz', 'deb']

            if any(name.endswith(suf) for suf in suffixes):
                checksum_file = Checksum.generate(self.__env, path)
                self.__storage.move_to_dist(checksum_file)
            self.__storage.move_to_dist(path)

        if self.__mac is not None:
            self.__mac.cleanup_keychain()
        if self.__win is not None:
            self.__win.cleanup_certificate()

    @staticmethod
    @log_group('pnpm install')
    def __restore_pnpm_dependencies() -> None:
        node_version = subprocess.check_output(
            'node --version',
            shell=True,
            encoding='utf8',
        ).strip()
        pnpm_version = subprocess.check_output(
            'pnpm --version',
            shell=True,
            encoding='utf8',
        ).strip()
        logger.info(
            f'Restoring dependencies using Node.js {node_version} and pnpm@{pnpm_version}',
        )
        ret_code = subprocess.call(
            'pnpm install --no-optional --frozen-lockfile',
            shell=True,
        )
        if ret_code != 0:
            logger.error('pnpm install failed')


def main() -> None:
    environment = Environment()
    environment.check_environment()

    storage = Storage()

    parser = argparse.ArgumentParser(description='Build rotki')
    parser.add_argument('--build', choices=['backend', 'frontend', 'full'], default='full')
    parser.add_argument(
        '--clean',
        action='store_true',
        default=False,
        help='Performs a clean build',
    )
    args = parser.parse_args()

    if args.clean:
        logger.info('Cleaning build directory')
        storage.clean()

    logger.info(f'starting build with {args.build}')

    mac, win = None, None
    if environment.is_mac():
        mac = MacPackaging(storage, environment)
    if environment.is_windows():
        win = WindowsPackaging(storage, environment)

    if args.build in {'backend', 'full'}:
        builder = BackendBuilder(storage, environment, mac, win)
        builder.clean()
        builder.build()

    if args.build in {'full', 'frontend'}:
        frontend_builder = FrontendBuilder(storage, environment, mac, win)
        frontend_builder.build()


if __name__ == '__main__':
    main()
