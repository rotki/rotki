from typing import NamedTuple, Optional

from pkg_resources import parse_version

from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.github import Github
from rotkehlchen.utils.misc import get_system_spec


class VersionCheckResult(NamedTuple):
    our_version: str
    latest_version: Optional[str] = None
    download_url: Optional[str] = None


def check_if_version_up_to_date() -> VersionCheckResult:
    """Checks if there is a newer Rotkehlchen version available for download

    If there is a remote query error return only our version.
    If there is no newer version for download returns only our current version and latest version.
    If yes returns (our_version_str, latest_version_str, download_url)
    """
    our_version_str = get_system_spec()['rotkehlchen']
    our_version = parse_version(our_version_str)

    github = Github()
    try:
        latest_version_str, url = github.get_latest_release()
    except RemoteError:
        # Completely ignore all remote errors. If Github has problems we just don't check now
        return VersionCheckResult(our_version=our_version_str)

    latest_version = parse_version(latest_version_str)

    if latest_version <= our_version:
        return VersionCheckResult(our_version=our_version_str, latest_version=latest_version_str)

    return VersionCheckResult(
        our_version=our_version_str,
        latest_version=latest_version_str,
        download_url=url,
    )
