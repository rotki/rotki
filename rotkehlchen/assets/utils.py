import logging
from typing import TYPE_CHECKING, List, Optional

from rotkehlchen.assets.asset import Asset, AssetWithOracles, EvmToken, UnderlyingToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import NotERC20Conformant
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def add_ethereum_token_to_db(token_data: EvmToken) -> EvmToken:
    """Adds an ethereum token to the DB and returns it

    May raise:
    - InputError if token already exists in the DB
    """
    globaldb = GlobalDBHandler()
    globaldb.add_asset(
        asset_id=token_data.identifier,
        asset_type=AssetType.EVM_TOKEN,
        data=token_data,
    )
    # This can, but should not raise UnknownAsset, DeserializationError
    return EvmToken(token_data.identifier, form_with_incomplete_data=True)


def get_or_create_evm_token(
        userdb: 'DBHandler',
        evm_address: ChecksumEvmAddress,
        chain: ChainID,
        token_kind: EvmTokenKind = EvmTokenKind.ERC20,
        symbol: Optional[str] = None,
        name: Optional[str] = None,
        decimals: Optional[int] = None,
        protocol: Optional[str] = None,
        underlying_tokens: Optional[List[UnderlyingToken]] = None,
        form_with_incomplete_data: bool = False,
        ethereum_manager: 'EthereumManager' = None,
) -> EvmToken:
    """Given a token address return the <EvmToken>

    If the token exists in the GlobalDB it's returned. If not it's created and added.

    If an ethereum_manager instance is passed then in the case that the token is not
    in the global DB it will be added and an attempt to get metadata will be made.

    Note: if the token already exists but the other arguments don't match the
    existing token will still be silently returned
    Note2: This entire function is designed so that it does not context switch away from
    its calling greenlet so it should be safe to call from multiple greenlets.

    May raise:
    - NotERC20Conformant exception if an ethereum manager is given to query
    and the given address does not have any of symbol, decimals and name
    - NotERC721Conformant exception if an ethereum manager is given to query
    and the given address does not conform to ERC721 spec
    """
    identifier = evm_address_to_identifier(
        address=evm_address,
        chain=chain,
        token_type=token_kind,
    )
    with userdb.get_or_create_evm_token_lock:
        try:
            ethereum_token = EvmToken(
                identifier=identifier,
                form_with_incomplete_data=form_with_incomplete_data,
            )
        except (UnknownAsset, DeserializationError):
            # It can happen that the asset exists but is missing basic information.
            # Check if it exists and if that is the case we fetch information.
            # The check above would fail if the identifier is not a token or name,
            # symbol or decimals is missing while form_with_incomplete_data is False
            try:
                asset_exists = Asset(identifier).check_existence() is not None
            except UnknownAsset:
                asset_exists = False

            log.info(
                f'Encountered unknown asset with address '
                f'{evm_address}. Adding it to the global DB',
            )

            if ethereum_manager is not None:
                if token_kind == EvmTokenKind.ERC20:
                    info = ethereum_manager.get_erc20_contract_info(evm_address)
                    decimals = info['decimals'] if decimals is None else decimals
                    symbol = info['symbol'] if symbol is None else symbol
                    name = info['name'] if name is None else name
                    if None in (decimals, symbol, name):
                        raise NotERC20Conformant(f'Token {evm_address} is not ERC20 conformant')  # noqa: E501  # pylint: disable=raise-missing-from

                elif token_kind == EvmTokenKind.ERC721:
                    info = ethereum_manager.get_erc721_contract_info(evm_address)
                    decimals = 0
                    if symbol is None:
                        symbol = info['symbol'] if info['symbol'] is not None else ''
                    if name is None:
                        name = info['name'] if info['name'] is not None else ''

                else:
                    raise NotERC20Conformant(f'Token {evm_address} is of uknown type')  # pylint: disable=raise-missing-from  # noqa: E501

            # Store the information in the database
            token_data = EvmToken.initialize(
                address=evm_address,
                chain=chain,
                token_kind=token_kind,
                name=name,
                decimals=decimals,
                symbol=symbol,
                protocol=protocol,
                underlying_tokens=underlying_tokens,
            )
            if asset_exists is True:
                # This means that we need to update the information in the database with the
                # newly queried data
                GlobalDBHandler().edit_evm_token(token_data)
            else:
                # This can but should not raise InputError since it should not already exist.
                ethereum_token = add_ethereum_token_to_db(
                    token_data=token_data,
                )

                with userdb.user_write() as cursor:
                    userdb.add_asset_identifiers(cursor, [ethereum_token.identifier])

    return ethereum_token


def get_crypto_asset_by_symbol(
        symbol: str,
        asset_type: Optional[AssetType] = None,
        evm_chain: Optional[ChainID] = None,
) -> Optional[AssetWithOracles]:
    """Gets an asset by symbol from the DB.

    If no asset with that symbol or multiple assets (except for EVM tokens) with the same
    symbol are found returns None. If all the results are evm tokens then the one from the
    preferred_chain is selected.
    """
    if symbol == 'ETH':
        return A_ETH.resolve_to_asset_with_oracles()  # ETH can be ETH and ETH2 in the DB

    assets_data = GlobalDBHandler().get_assets_with_symbol(
        symbol=symbol,
        asset_type=asset_type,
        chain=evm_chain,
    )
    if len(assets_data) != 1:
        return None

    return assets_data[0]


def symbol_to_asset_or_token(
        symbol: str,
        evm_chain: Optional[ChainID] = None,
) -> AssetWithOracles:
    """Tries to turn the given symbol to an asset or an ethereum Token

    May raise:
    - UnknownAsset if an asset can't be found by the symbol or if
    more than one tokens match this symbol
    """
    asset: AssetWithOracles
    try:
        asset = Asset(symbol).resolve_to_asset_with_oracles()
    except UnknownAsset:
        # Let's search by symbol if a single asset matches
        maybe_asset = get_crypto_asset_by_symbol(symbol=symbol, evm_chain=evm_chain)
        if maybe_asset is None:
            raise
        asset = maybe_asset

    return asset


def symbol_to_ethereum_token(symbol: str, evm_chain: Optional[ChainID] = None) -> EvmToken:
    """Tries to turn the given symbol to an ethereum token

    May raise:
    - UnknownAsset if an ethereum token can't be found by the symbol or if
    more than one tokens match this symbol
    """
    maybe_asset = get_crypto_asset_by_symbol(
        symbol=symbol,
        asset_type=AssetType.EVM_TOKEN,
        evm_chain=evm_chain,
    )
    if maybe_asset is None:
        raise UnknownAsset(symbol)

    return maybe_asset.resolve_to_evm_token()
