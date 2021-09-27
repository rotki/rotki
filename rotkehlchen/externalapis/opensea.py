import dataclasses
import json
import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, Union, overload

import gevent
import requests
from eth_utils import to_checksum_address
from typing_extensions import Literal

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import NFT_DIRECTIVE, ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.serialization.deserialize import deserialize_optional_fval
from rotkehlchen.typing import ChecksumEthAddress, ExternalService
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

ASSETS_MAX_LIMIT = 50  # according to opensea docs
CONTRACTS_MAX_LIMIT = 300  # according to opensea docs

logger = logging.getLogger(__name__)


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=False)  # noqa: E501
class Collection:
    name: str
    banner_image: str
    description: str
    large_image: str
    floor_price: Optional[FVal] = None

    def serialize(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'banner_image': self.banner_image,
            'description': self.description,
            'large_image': self.large_image,
            'floor_price': str(self.floor_price) if self.floor_price else None,
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


class Opensea(ExternalServiceWithApiKey):
    """https://docs.opensea.io/reference/api-overview"""
    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator) -> None:
        super().__init__(database=database, service_name=ExternalService.OPENSEA)
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.collections: Dict[str, Collection] = {}

    @overload
    def _query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['assets'],
            options: Optional[Dict[str, Any]] = None,
            timeout: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        ...

    @overload
    def _query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['collections'],
            options: Optional[Dict[str, Any]] = None,
            timeout: Optional[Tuple[int, int]] = None,
    ) -> List[Dict[str, Any]]:
        ...

    def _query(
            self,
            endpoint: Literal['assets', 'collections'],
            options: Optional[Dict[str, Any]] = None,
            timeout: Optional[Tuple[int, int]] = None,
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
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

    def _deserialize_nft(
            self,
            entry: Dict[str, Any],
            owner_address: ChecksumEthAddress,
            eth_usd_price: FVal,
    ) -> 'NFT':
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
                eth_price = FVal(last_sale['payment_token']['eth_price'])
                last_price_in_eth = amount * eth_price
            else:
                last_price_in_eth = ZERO

            floor_price = ZERO
            # NFT might not be part of a collection
            if 'collection' in entry:
                saved_entry = self.collections.get(entry['collection']['name'])
                if saved_entry is None:
                    # we haven't got this collection in memory. Query opensea for info
                    self.gather_account_collections(account=owner_address)
                    # try to get the info again
                    saved_entry = self.collections.get(entry['collection']['name'])

                if saved_entry:
                    collection = saved_entry
                    if saved_entry.floor_price is not None:
                        floor_price = saved_entry.floor_price
                else:  # should not happen. That means collections endpoint doesnt return anything
                    collection_data = entry['collection']
                    collection = Collection(
                        name=collection_data['name'],
                        banner_image=collection_data['banner_image_url'],
                        description=collection_data['description'],
                        large_image=collection_data['large_image_url'],
                    )

            price_in_eth = max(last_price_in_eth, floor_price)
            price_in_usd = price_in_eth * eth_usd_price
            token_id = entry['asset_contract']['address'] + '_' + entry['token_id']
            return NFT(
                token_identifier=NFT_DIRECTIVE + token_id,
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

    def gather_account_collections(self, account: ChecksumEthAddress) -> None:
        """Gathers account collection information and keeps them in memory"""
        offset = 0
        options = {'offset': offset, 'limit': CONTRACTS_MAX_LIMIT, 'asset_owner': account}  # noqa: E501

        raw_result: List[Dict[str, Any]] = []
        while True:
            result = self._query(endpoint='collections', options=options)
            raw_result.extend(result)
            if len(result) != CONTRACTS_MAX_LIMIT:
                break

            # else continue by paginating
            offset += CONTRACTS_MAX_LIMIT
            options['offset'] = offset

        for entry in raw_result:
            if len(entry['primary_asset_contracts']) == 0:
                continue  # skip if no contract (opensea makes everything a collection of 1)
            name = entry['name']
            self.collections[name] = Collection(
                name=name,
                banner_image=entry['banner_image_url'],
                description=entry['description'],
                large_image=entry['large_image_url'],
                floor_price=deserialize_optional_fval(
                    value=entry['stats']['floor_price'],
                    name='floor_price',
                    location='opensea',
                ),
            )

    def get_account_nfts(self, account: ChecksumEthAddress) -> List[NFT]:
        """May raise RemoteError"""
        offset = 0
        options = {'order_direction': 'desc', 'offset': offset, 'limit': ASSETS_MAX_LIMIT, 'owner': account}  # noqa: E501
        eth_usd_price = Inquirer.find_usd_price(A_ETH)

        raw_result = []
        while True:
            result = self._query(endpoint='assets', options=options)
            raw_result.extend(result['assets'])  # pylint: disable=unsubscriptable-object
            if len(result['assets']) != ASSETS_MAX_LIMIT:  # pylint: disable=unsubscriptable-object
                break

            # else continue by paginating
            offset += ASSETS_MAX_LIMIT
            options['offset'] = offset

        nfts = []
        for entry in raw_result:
            try:
                nfts.append(self._deserialize_nft(
                    entry=entry,
                    owner_address=account,
                    eth_usd_price=eth_usd_price,
                ))
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
