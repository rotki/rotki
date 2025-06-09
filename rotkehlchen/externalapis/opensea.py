import dataclasses
import logging
import re
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple

import requests
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_fval,
    deserialize_int,
    deserialize_optional_to_optional_fval,
)
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, ExternalService
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.concurrency import sleep

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

ASSETS_MAX_LIMIT: Final = 50  # according to opensea docs


ERC721_RE: Final = re.compile(r'eip155:1/erc721:(.*?)/(.*)')

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _read_floor_asset_price_from_collection(
        floor_price_symbol: str,
        collection_payment_tokens: list[dict[str, str]],
) -> Asset:
    """
    Get the asset currency for the floor price reported by opensea using the list
    of assets listed in the collection's payment tokens.

    TODO: The api has a bug reported in the ticket #1455100 and the chain is reported
    always as ethereum even if the asset is not an ethereum token.
    When fixed adjust this function to use the chain.

    May raise:
    - UnknownAsset if the token wasn't found in the collection payment tokens.
    """
    for payment_token in collection_payment_tokens:
        if payment_token.get('symbol') == floor_price_symbol:
            try:
                address = to_checksum_address(payment_token['address'])
            except KeyError:
                log.error(f'Skipping opensea payment token because the address key is not present. {payment_token=}')  # noqa: E501
                continue

            with GlobalDBHandler().conn.read_ctx() as cursor:
                asset_identifier = cursor.execute(  # we consider as correct to query only by address knowing that the same address could exist in different chains until opensea provides the correct chain value in the api  # noqa: E501
                    'SELECT identifier FROM evm_tokens WHERE address=?',
                    (address,),
                ).fetchone()
                if asset_identifier is not None:
                    return Asset(asset_identifier[0])

    raise UnknownAsset(
        'Did not find a valid token matching the symbol '
        f'{floor_price_symbol} in {collection_payment_tokens}',
    )


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=False)  # noqa: E501
class Collection:
    name: str
    banner_image: str | None
    description: str | None
    large_image: str
    floor_price_asset: Asset = A_ETH
    floor_price: FVal | None = None

    def serialize(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'banner_image': self.banner_image,
            'description': self.description,
            'large_image': self.large_image,
            'floor_price': str(self.floor_price) if self.floor_price else None,
            'floor_price_asset': self.floor_price_asset.identifier,
        }


class NFT(NamedTuple):
    token_identifier: str
    background_color: str | None
    image_url: str | None
    name: str | None
    external_link: str | None
    permalink: str | None
    price_asset: Asset
    price_in_asset: FVal
    price_usd: FVal
    collection: Collection | None

    def serialize(self) -> dict[str, Any]:
        return {
            'token_identifier': self.token_identifier,
            'background_color': self.background_color,
            'image_url': self.image_url if self.image_url not in {None, ''} else None,
            'name': self.name,
            'external_link': self.external_link,
            'permalink': self.permalink,
            'price_asset': self.price_asset.identifier,
            'price_in_asset': str(self.price_in_asset),
            'price_usd': str(self.price_usd),
            'collection': self.collection.serialize() if self.collection else None,
        }


class Opensea(ExternalServiceWithApiKey):
    """https://docs.opensea.io/reference/api-overview"""
    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            ethereum_inquirer: EthereumInquirer,
    ) -> None:
        super().__init__(database=database, service_name=ExternalService.OPENSEA)
        self.msg_aggregator = msg_aggregator
        self.session = create_session()
        self.session.headers.update({
            'Content-Type': 'application/json',
        })
        self.collections: dict[str, Collection] = {}
        self.backup_key: str | None = None
        self.ethereum_inquirer = ethereum_inquirer
        self.eth_asset = ethereum_inquirer.native_token

    def _query(
            self,
            endpoint: Literal['assets', 'collectionstats', 'asset', 'collection'],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        """May raise RemoteError"""
        api_key = self._get_api_key()
        if api_key is not None:
            self.session.headers.update({'X-API-KEY': api_key})

        if endpoint == 'collectionstats':
            query_str = f'https://api.opensea.io/api/v2/collections/{options["name"]}/stats'  # type: ignore
        elif endpoint == 'collection':
            query_str = f'https://api.opensea.io/api/v2/collections/{options["collection_slug"]}'  # type: ignore
        elif endpoint == 'asset':
            query_str = f'https://api.opensea.io/api/v2/chain/ethereum/contract/{options["address"]}/nfts/{options["item_id"]}'  # type: ignore
            options = None
        else:
            query_str = f'https://api.opensea.io/api/v2/chain/ethereum/account/{options["address"]}/nfts'  # type: ignore

        backoff = 1
        backoff_limit = 33
        timeout = timeout or CachedSettings().get_timeout_tuple()
        response = None
        while backoff < backoff_limit:
            log.debug(f'Querying opensea: {query_str}')
            try:
                response = self.session.get(
                    query_str,
                    params=options,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'Opensea API request {query_str} failed due to {e!s}',
                ) from e

            if response.status_code != 200:
                if api_key is None and self.backup_key is None:
                    self.backup_key = '04ea654d84cd4b2b8da25ec41ca1a9a4'
                    self.session.headers.update({'X-API-KEY': self.backup_key})

                log.debug(
                    f'Got {response.status_code} response from opensea. Will backoff for {backoff} seconds',  # noqa: E501
                )
                sleep(backoff)
                backoff *= 2
                if backoff >= backoff_limit:
                    raise RemoteError(
                        f'Reached opensea backoff limit after we incrementally backed off '
                        f'for {response.url}',
                    )
                continue

            break  # else we found response so let's break off the loop

        assert response is not None  # if we get here response is populated
        if response.status_code != 200:
            raise RemoteError(
                f'Opensea API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = response.json()
        except JSONDecodeError as e:
            raise RemoteError(
                f'Opensea API request {response.url} returned invalid '
                f'JSON response: {response.text}',
            ) from e

        return json_ret

    def _deserialize_nft(
            self,
            entry: dict[str, Any],
            owner_address: ChecksumEvmAddress,
            eth_usd_price: FVal,
    ) -> 'NFT':
        """May raise:

        - DeserializationError if the given dict can't be deserialized or
        we couldn't read the collection.
        """
        if not isinstance(entry, dict):
            raise DeserializationError(
                f'Failed to deserialize NFT value from non dict value: {entry}',
            )

        try:
            last_sale: dict[str, Any] | None = entry.get('last_sale')
            if last_sale is not None and last_sale.get('payment_token') is not None:
                if last_sale['payment_token']['symbol'] in {'ETH', 'WETH'}:
                    payment_asset = self.eth_asset
                else:
                    payment_asset = get_or_create_evm_token(
                        userdb=self.db,
                        evm_address=deserialize_evm_address(last_sale['payment_token']['address']),
                        chain_id=ChainID.ETHEREUM,
                        token_kind=EvmTokenKind.ERC20,
                        evm_inquirer=self.ethereum_inquirer,
                    )

                amount = asset_normalized_value(
                    amount=deserialize_int(last_sale['total_price']),
                    asset=payment_asset,
                )
                eth_price = deserialize_fval(
                    value=last_sale['payment_token']['eth_price'],
                    name='payment_token - eth_price',
                    location='opensea entry deserialization',
                )
                last_price_in_eth = amount * eth_price
            else:
                last_price_in_eth = ZERO

            floor_price, floor_price_asset = ZERO, A_ETH
            collection = None
            # NFT might not be part of a collection
            if 'collection' in entry:
                saved_entry = self.collections.get(entry['collection'])
                if saved_entry is None:
                    try:
                        # we haven't got this collection in memory. Query opensea for info
                        self.gather_account_collections(account=owner_address)
                    except RemoteError as e:
                        log.error(f'Failed to query account collections for {owner_address}. {e}')

                    # try to get the info again
                    saved_entry = self.collections.get(entry['collection'])

                if saved_entry:
                    collection = saved_entry
                    if saved_entry.floor_price is not None:
                        floor_price = saved_entry.floor_price
                        floor_price_asset = saved_entry.floor_price_asset
                else:  # should not happen. That means collections endpoint doesnt return anything
                    raise DeserializationError(
                        f'Could not find collection {entry["collection"]} in opensea collections '
                        f'endpoint',
                    )

            last_price_in_usd = last_price_in_eth * eth_usd_price
            floor_price_in_usd = floor_price * Inquirer.find_usd_price(asset=floor_price_asset) if floor_price != ZERO else ZERO  # noqa: E501

            if floor_price_in_usd > last_price_in_usd:
                price_in_asset = floor_price
                price_asset = floor_price_asset
                price_in_usd = floor_price_in_usd
            else:
                price_in_asset = last_price_in_eth
                price_asset = A_ETH
                price_in_usd = last_price_in_usd

            try:
                token_id = f'{to_checksum_address(entry["contract"])}_{entry["identifier"]}'
            except (ValueError, TypeError) as e:
                raise DeserializationError(
                    f'Failed to checksum NFT contract address for {entry}',
                ) from e

            if entry['token_standard'] == 'erc1155':
                token_id += f'_{owner_address!s}'

            return NFT(  # can raise KeyError due to arg init
                token_identifier=NFT_DIRECTIVE + token_id,
                background_color=None,
                image_url=entry['image_url'],
                name=entry['name'],
                external_link=entry['metadata_url'],
                permalink=entry['opensea_url'],
                price_in_asset=price_in_asset,
                price_asset=price_asset,
                price_usd=price_in_usd,
                collection=collection,
            )
        except KeyError as e:
            raise DeserializationError(f'Could not find key {e!s} when processing Opensea NFT data') from e  # noqa: E501

    def _consume_assets_endpoint(self, account: ChecksumEvmAddress) -> list[dict[str, Any]]:
        """
        Query all the nfts for the provided account and return the information
        provided by opensea.
        May raise:
        - RemoteError
        """
        options = {'next': None, 'limit': ASSETS_MAX_LIMIT, 'address': account}
        raw_result: list[dict[str, Any]] = []

        while True:
            result = self._query(endpoint='assets', options=options)
            log.debug(f'Got Opensea response for {account} assets {result=}')
            raw_result.extend(result['nfts'])
            if 'next' not in result or len(result['nfts']) != ASSETS_MAX_LIMIT:
                break

            # else continue by paginating
            options['next'] = result['next']

        return raw_result

    def gather_account_collections(self, account: ChecksumEvmAddress) -> None:
        """
        Gathers account collection information and keeps them in memory
        May raise:
        - RemoteError
        """
        raw_result = self._consume_assets_endpoint(account=account)
        for entry in raw_result:
            try:
                options = {'collection_slug': entry['collection']}
                collection = self._query(endpoint='collection', options=options)
                slug = collection['collection']
                if slug in self.collections:
                    continue  # do not requery already queried collection

                # To get the floor price we need to query a different endpoint
                # https://github.com/rotki/rotki/issues/3676
                stats_result = self._query(
                    endpoint='collectionstats', options={'name': entry['collection']},
                )
                log.debug(stats_result)
                raw_floor_price = (
                    stats_result['total']['floor_price'] or stats_result['total']['average_price']
                )
                floor_price = deserialize_optional_to_optional_fval(
                    value=raw_floor_price,
                    name='floor price',
                    location='opensea',
                )

                if (
                    len(payment_tokens := collection.get('payment_tokens', [])) == 0 or
                    stats_result['total']['floor_price_symbol'] in ('', 'ETH')
                ):
                    floor_price_asset = A_ETH
                else:  # if the price is in something else than eth find the token
                    try:
                        floor_price_asset = _read_floor_asset_price_from_collection(
                            floor_price_symbol=stats_result['total']['floor_price_symbol'],
                            collection_payment_tokens=payment_tokens,
                        )
                    except UnknownAsset as e:  # we failed to find the token. Ignore the price
                        log.error(f"Could not read asset in opensea floor price with symbol {stats_result['total']['floor_price_symbol']}. Ignoring it. {e}")  # noqa: E501
                        floor_price_asset = A_ETH
                        floor_price = ZERO

                self.collections[slug] = Collection(
                    name=collection['name'],
                    banner_image=collection['banner_image_url'],
                    description=collection['description'],
                    large_image=collection['image_url'],
                    floor_price=floor_price,
                    floor_price_asset=floor_price_asset,
                )
            except KeyError as e:
                log.error(
                    f'Failed to get opensea collection information for {account=} due '
                    f'to missing key {e} in {entry=}. Skipping it',
                )

    def get_account_nfts(self, account: ChecksumEvmAddress) -> list[NFT]:
        """May raise RemoteError"""
        eth_usd_price = Inquirer.find_usd_price(A_ETH)
        raw_result = self._consume_assets_endpoint(account=account)
        nfts = []

        for entry in raw_result:
            log.debug(f'Deserializing opensea nft data owned by {account=}: {entry}')
            try:
                nfts.append(self._deserialize_nft(
                    entry=entry,
                    owner_address=account,
                    eth_usd_price=eth_usd_price,
                ))
            except (UnknownAsset, DeserializationError) as e:
                log.error(
                    f'Skipping detected NFT for {account} due to {e!s}. '
                    f'Problematic entry: {entry} ',
                )

        return nfts

    def get_nft_image(
            self,
            nft_address: str,
    ) -> str | None:
        """Returns the url of the image of an nft or None in error"""
        match = ERC721_RE.search(nft_address)
        if match is None:
            return None

        address = match.group(1)
        item_id = match.group(2)
        try:
            result = self._query(
                endpoint='asset',
                options={
                    'address': address,
                    'item_id': item_id,
                },
            )
            return result['nft']['image_url']
        except (RemoteError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Failed to find key {msg} in opensea result'
            log.error(f'Could not query {nft_address} opensea nft image due to {msg}')
            return None
