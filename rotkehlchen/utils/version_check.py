import logging
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, NamedTuple, Optional

from packaging.version import InvalidVersion, Version

from rotkehlchen.errors.misc import RemoteError

if TYPE_CHECKING:
    from rotkehlchen.externalapis.github import Github


logger = logging.getLogger(__name__)


def get_system_spec() -> dict[str, str]:
    """Collect information about the system and installation."""
    if sys.platform == 'darwin':
        system_info = f'macOS {platform.mac_ver()[0]} {platform.architecture()[0]}'
    else:
        system_info = '{} {} {} {}'.format(
            platform.system(),
            '_'.join(platform.architecture()),
            platform.release(),
            platform.machine(),
        )

    try:
        rotki_version = version('rotkehlchen')
    except (PackageNotFoundError, ValueError) as e:
        logger.error(f'Failed to retrieve rotki version due to {e}. Defaulting to 0.0.0')
        rotki_version = '0.0.0'

    return {
        'rotkehlchen': rotki_version,
        'python_implementation': platform.python_implementation(),
        'python_version': platform.python_version(),
        'system': system_info,
    }


class VersionCheckResult(NamedTuple):
    our_version: Version
    latest_version: Version | None = None
    download_url: str | None = None


def get_current_version(github: Optional['Github'] = None) -> VersionCheckResult:
    """Get current version of rotki. If a github is passed then it is contacted to ask
    if there is any updates.

    If there is a remote query error return only our version.
    If there is no newer version for download returns only our current version and latest version.
    If there is an update returns (our_version, latest_version, download_url)
    """
    our_version = Version(get_system_spec()['rotkehlchen'])
    if github is not None:
        try:
            latest_version_str, url = github.get_latest_release()
        except RemoteError:
            # Completely ignore all remote errors. If Github has problems we just don't check now
            return VersionCheckResult(our_version=our_version)

        try:
            latest_version = Version(latest_version_str)
        except (InvalidVersion, TypeError):
            return VersionCheckResult(our_version=our_version)

        if latest_version <= our_version:
            return VersionCheckResult(
                our_version=our_version,
                latest_version=latest_version,
            )

        return VersionCheckResult(
            our_version=our_version,
            latest_version=latest_version,
            download_url=url,
        )

    return VersionCheckResult(our_version=our_version)
