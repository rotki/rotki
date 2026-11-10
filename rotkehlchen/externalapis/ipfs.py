import logging
from typing import Any, Final
from urllib.parse import urlparse, urlunparse

import requests

from rotkehlchen.errors.misc import IPFSRemoteError, RemoteError
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

    Accepts `https://host`, `https://host/ipfs` or `https://host/ipfs/`, optionally with a
    query string such as `?token=...` which is sent along with every request. The query
    must already be in the percent-encoded form requests sends, so that the query in the
    url's errors is the one redacted from them. The error messages never include the url
    since it may hold a secret.

    May raise:
        ValueError: if the url contains userinfo credentials, parameters or a fragment,
        is not an http(s) url or its query is not percent-encoded.
    """
    parsed = urlparse(url.strip())
    if parsed.username is not None or parsed.password is not None:
        raise ValueError('IPFS gateway URL must not contain credentials in the userinfo')

    if parsed.params != '' or parsed.fragment != '':
        raise ValueError('IPFS gateway URL must not contain path parameters or a fragment')

    if parsed.scheme not in {'http', 'https'} or parsed.netloc == '':
        raise ValueError('IPFS gateway must be an http(s) url')

    if not (path := parsed.path.rstrip('/')).endswith('/ipfs'):
        path += '/ipfs'
    normalized = urlunparse(parsed._replace(path=f'{path}/'))
    try:
        (prepared := requests.PreparedRequest()).prepare_url(url=normalized, params=None)
    except requests.exceptions.RequestException as e:
        raise ValueError('IPFS gateway URL is not a valid url') from e

    if prepared.url is None or urlparse(prepared.url).query != parsed.query:
        raise ValueError(
            'IPFS gateway URL query must be in canonical percent-encoded form, '
            'e.g. %20 for a space and %2F instead of %2f',
        )

    return normalized


def redact_ipfs_gateway_url(url: str) -> str:
    """Return the gateway url without its query string, which may hold an access token."""
    return urlunparse(urlparse(url.strip())._replace(query=''))


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

        The query string of a gateway may hold an access token, so it never reaches the
        logs or the raised error. normalize_ipfs_gateway_url guarantees that the query is
        sent as written, so it is also the form that appears in the request's errors.

        May raise:
            IPFSRemoteError: if every gateway failed. The error lists the reason for each.
        """
        failures: list[str] = []
        for gateway in self.gateways:
            parsed = urlparse(gateway)
            url = urlunparse(parsed._replace(path=f'{parsed.path}{cid}'))
            try:
                return query_file(url, is_json=True)
            except RemoteError as e:
                shown = redact_ipfs_gateway_url(gateway)
                reason = str(e).replace(parsed.query, '<redacted>') if parsed.query else str(e)
                log.warning('IPFS gateway %s failed to serve %s: %s', shown, cid, reason)
                failures.append(f'{shown}: {reason}')

        raise IPFSRemoteError(
            f'Could not fetch IPFS content {cid} from any gateway. ' + '; '.join(failures),
        )
