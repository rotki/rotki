import json
import logging
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import gevent
import requests
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress, ExternalService
from rotkehlchen.user_messages import MessagesAggregator

MAX_LIMIT = 50  # according to opensea docs

logger = logging.getLogger(__name__)


class Collection(NamedTuple):
    name: str
    banner_image: str
    description: str
    large_image: str

    def serialize(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'banner_image': self.banner_image,
            'description': self.description,
            'large_image': self.large_image,
        }


class NFT(NamedTuple):
    token_identifier: str
    background_color: Optional[str]
    image_url: Optional[str]
    name: Optional[str]
    external_link: Optional[str]
    permalink: Optional[str]
    price_eth: FVal
    price_usd: FVal
    collection: Collection

    def serialize(self) -> Dict[str, Any]:
        return {
            'token_identifier': self.token_identifier,
            'background_color': self.background_color,
            'image_url': self.image_url if self.image_url not in (None, '') else None,
            'name': self.name,
            'external_link': self.external_link,
            'permalink': self.permalink,
            'price_eth': str(self.price_eth),
            'price_usd': str(self.price_usd),
            'collection': self.collection.serialize(),
        }

    @staticmethod
    def deserialize(entry: Dict[str, Any]) -> 'NFT':
        """May raise:

        - DeserializationError if the given dict can't be deserialized
        - UnknownAsset if the given payment token isn't known
        """
        if not isinstance(entry, dict):
            raise DeserializationError(
                f'Failed to deserialize NFT value from non dict value: {entry}',
            )

        try:
            last_sale = entry.get('last_sale')
            if last_sale:
                if last_sale['payment_token']['symbol'] == 'ETH':
                    payment_token = A_ETH
                else:
                    payment_token = EthereumToken(
                        to_checksum_address(last_sale['payment_token']['symbol']),
                    )

                amount = asset_normalized_value(int(last_sale['total_price']), payment_token)
                usd_price = FVal(last_sale['payment_token']['usd_price'])
                eth_price = FVal(last_sale['payment_token']['eth_price'])
                price_in_eth = amount * eth_price
                price_in_usd = amount * usd_price
            else:
                price_in_eth = ZERO
                price_in_usd = ZERO

            # NFT might not be part of a collection
            if 'collection' in entry:
                collection_data = entry['collection']
                collection = Collection(
                    name=collection_data['name'],
                    banner_image=collection_data['banner_image_url'],
                    description=collection_data['description'],
                    large_image=collection_data['large_image_url'],
                )

            return NFT(
                token_identifier=entry['token_id'],
                background_color=entry['background_color'],
                image_url=entry['image_url'],
                name=entry['name'],
                external_link=entry['external_link'],
                permalink=entry['permalink'],
                price_eth=price_in_eth,
                price_usd=price_in_usd,
                collection=collection,
            )
        except KeyError as e:
            raise DeserializationError(f'Could not find key {str(e)} when processing Opensea NFT data') from e  # noqa: E501


class Opensea(ExternalServiceWithApiKey):
    """https://docs.opensea.io/reference/api-overview"""
    def __init__(self, database: DBHandler, msg_aggregator: MessagesAggregator) -> None:
        super().__init__(database=database, service_name=ExternalService.OPENSEA)
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})

    def _query(
            self,
            endpoint: str,
            options: Optional[Dict[str, Any]] = None,
            timeout: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """May raise RemoteError"""
        query_str = f'https://api.opensea.io/api/v1/{endpoint}'

        backoff = 1
        backoff_limit = 33
        while backoff < backoff_limit:
            logger.debug(f'Querying opensea: {query_str}')
            try:
                response = self.session.get(
                    query_str,
                    params=options,
                    timeout=timeout if timeout else DEFAULT_TIMEOUT_TUPLE,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'Opensea API request {response.url} failed due to {str(e)}'
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                ) from e

            if response.status_code == 429:
                logger.debug(
                    f'Got 429 from opensea. Will backoff for {backoff} seconds',
                )
                gevent.sleep(backoff)
                backoff = backoff * 2
                if backoff >= backoff_limit:
                    raise RemoteError(
                        f'Reached opensea backoff limit after we incrementally backed off '
                        f'for {response.url}',
                    )
                continue

            break  # else we found response so let's break off the loop

        if response.status_code != 200:
            raise RemoteError(
                f'Opensea API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = json.loads(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Opensea API request {response.url} returned invalid '
                f'JSON response: {response.text}',
            ) from e

        return json_ret

    def get_account_nfts(self, account: ChecksumEthAddress) -> List[NFT]:
        """May raise RemoteError"""
        offset = 0
        options = {'order_direction': 'desc', 'offset': offset, 'limit': MAX_LIMIT, 'owner': account}  # noqa: E501

        raw_result = []
        while True:
            result = self._query(endpoint='assets', options=options)
            raw_result.extend(result['assets'])
            if len(result['assets']) != MAX_LIMIT:
                break

            # else continue by paginating
            offset += MAX_LIMIT
            options['offset'] = offset

        nfts = []
        for entry in raw_result:
            try:
                nfts.append(NFT.deserialize(entry))
            except (UnknownAsset, DeserializationError) as e:
                self.msg_aggregator.add_warning(
                    f'Skipping detected NFT for {account} due to {str(e)}. '
                    f'Check out logs for more details',
                )
                logger.warning(
                    f'Skipping detected NFT for {account} due to {str(e)}. '
                    f'Problematic entry: {entry} ',
                )

        return nfts
