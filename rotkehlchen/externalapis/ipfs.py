import logging
from typing import Any, Final
from urllib.parse import urlparse

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.network import query_file

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Public path-style gateways, tried in order after the user's own gateway (if any).
# Public gateways rate limit aggressively, so the list is only a best effort. These are the ones
# that served the Lido CSM rewards tree when probed (ipfs.io, dweb.link, w3s.link and
# nftstorage.link answered 429, and 4everland.io/ipfs answered 403). 4everland's own host is
# slow but works, so it goes last.
DEFAULT_IPFS_GATEWAYS: Final = (
    'https://gateway.pinata.cloud/ipfs/',
    'https://ipfs.filebase.io/ipfs/',
    'https://ipfs.4everland.io/ipfs/',
)


def normalize_ipfs_gateway_url(url: str) -> str:
    """Normalize a user provided gateway to a path style base url ending in `/ipfs/`.

    Accepts `https://host`, `https://host/ipfs` or `https://host/ipfs/`.

    May raise:
        ValueError: if the url is not an http(s) url.
    """
    parsed = urlparse(url := url.strip())
    if parsed.scheme not in {'http', 'https'} or parsed.netloc == '':
        raise ValueError(f'IPFS gateway "{url}" must be an http(s) url')

    if not (url := url.rstrip('/')).endswith('/ipfs'):
        url += '/ipfs'
    return f'{url}/'


class IPFSGateway:
    """Resolves IPFS content by trying a list of HTTP gateways until one serves it.

    The optional custom gateway is tried first, then DEFAULT_IPFS_GATEWAYS.
    """

    def __init__(self, custom_gateway: str | None = None) -> None:
        gateways: list[str] = []
        if custom_gateway:  # empty/None means not set
            gateways.append(normalize_ipfs_gateway_url(custom_gateway))
        gateways.extend(x for x in DEFAULT_IPFS_GATEWAYS if x not in gateways)
        self.gateways: Final = tuple(gateways)

    def query_json(self, cid: str) -> dict[str, Any]:
        """Fetch the json document stored under the given cid from the first gateway
        that serves it.

        May raise:
            RemoteError: if every gateway failed. The error lists the reason for each.
        """
        failures: list[str] = []
        for gateway in self.gateways:
            try:
                return query_file(f'{gateway}{cid}', is_json=True)
            except RemoteError as e:
                log.warning('IPFS gateway %s failed to serve %s: %s', gateway, cid, e)
                failures.append(f'{gateway}: {e}')

        raise RemoteError(
            f'Could not fetch IPFS content {cid} from any gateway. ' + '; '.join(failures),
        )
