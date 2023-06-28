import platform
import sys
from typing import NamedTuple, Optional

import pkg_resources

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.github import Github  # to avoid circulat import


def get_system_spec() -> dict[str, str]:
    """Collect information about the system and installation."""
    if sys.platform == 'darwin':
        system_info = 'macOS {} {}'.format(
            platform.mac_ver()[0],
            platform.architecture()[0],
        )
    else:
        system_info = '{} {} {} {}'.format(
            platform.system(),
            '_'.join(platform.architecture()),
            platform.release(),
            platform.machine(),
        )

    system_spec = {
        # used to be require 'rotkehlchen.__name__' but as long as setup.py
        # target differs from package we need this
        'rotkehlchen': pkg_resources.require('rotkehlchen')[0].version,
        'python_implementation': platform.python_implementation(),
        'python_version': platform.python_version(),
        'system': system_info,
    }
    return system_spec


class VersionCheckResult(NamedTuple):
    our_version: str
    latest_version: Optional[str] = None
    download_url: Optional[str] = None


def get_current_version(check_for_updates: bool) -> VersionCheckResult:
    """Get current version of rotki. If check_for_updates is set to true it also checks
    if a new version is available.

    If there is a remote query error return only our version.
    If there is no newer version for download returns only our current version and latest version.
    If yes returns (our_version_str, latest_version_str, download_url)
    """
    our_version_str = get_system_spec()['rotkehlchen']

    if check_for_updates:
        our_version = pkg_resources.parse_version(our_version_str)
        github = Github()
        try:
            latest_version_str, url = github.get_latest_release()
        except RemoteError:
            # Completely ignore all remote errors. If Github has problems we just don't check now
            return VersionCheckResult(our_version=our_version_str)

        latest_version = pkg_resources.parse_version(latest_version_str)
        if latest_version <= our_version:
            return VersionCheckResult(
                our_version=our_version_str,
                latest_version=latest_version_str,
            )

        return VersionCheckResult(
            our_version=our_version_str,
            latest_version=latest_version_str,
            download_url=url,
        )

    return VersionCheckResult(our_version=our_version_str)
