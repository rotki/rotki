import platform
import sys
from typing import TYPE_CHECKING, NamedTuple, Optional

import pkg_resources

from rotkehlchen.errors.misc import RemoteError

if TYPE_CHECKING:
    from rotkehlchen.externalapis.github import Github


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


def get_current_version(github: Optional['Github'] = None) -> VersionCheckResult:
    """Get current version of rotki. If a github is passed then it is contacted to ask
    if there is any updates.

    If there is a remote query error return only our version.
    If there is no newer version for download returns only our current version and latest version.
    If there is an update returns (our_version_str, latest_version_str, download_url)
    """
    our_version_str = get_system_spec()['rotkehlchen']

    if github is not None:
        our_version = pkg_resources.parse_version(our_version_str)
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
