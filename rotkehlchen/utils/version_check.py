from typing import Optional, Tuple

from pkg_resources import parse_version

from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.github import Github
from rotkehlchen.utils.misc import get_system_spec


def check_if_version_up_to_date() -> Optional[Tuple[str, str, str]]:
    """Checks if there is a newer Rotkehlchen version available for download

    If not returns None
    If yes returns a tuple: (our_version_str, latest_version_str, url)
    """
    our_version_str = get_system_spec()['rotkehlchen']
    our_version = parse_version(our_version_str)

    github = Github()
    try:
        latest_version_str, url = github.get_latest_release()
    except RemoteError:
        # Completely ignore all remote errors. If Github has problems we just don't check now
        return None

    latest_version = parse_version(latest_version_str)

    if latest_version <= our_version:
        return None

    return our_version_str, latest_version_str, url
