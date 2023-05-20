import logging
from typing import TYPE_CHECKING, NamedTuple, Optional

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, AssetWithOracles, EvmToken, UnderlyingToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import NotERC20Conformant
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, EVMTxHash

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def add_evm_token_to_db(token_data: EvmToken) -> EvmToken:
    """Adds an evm token to the DB and returns it

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
    return EvmToken(token_data.identifier)


def _query_or_get_given_token_info(
        evm_inquirer: 'EvmNodeInquirer',
        evm_address: ChecksumEvmAddress,
        name: Optional[str],
        symbol: Optional[str],
        decimals: Optional[int],
        token_kind: EvmTokenKind,
) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Query ethereum to retrieve basic contract information for the given address.
    If the contract is missing any of the queried methods then the respective value
    given as parameter to this function is used.
    May raise:
    - NotERC20Conformant
    """
    if token_kind == EvmTokenKind.ERC20:
        info = evm_inquirer.get_erc20_contract_info(evm_address)
        decimals = info['decimals'] if decimals is None else decimals
        symbol = info['symbol'] if symbol is None else symbol
        name = info['name'] if name is None else name
        if None in (decimals, symbol, name):
            raise NotERC20Conformant(f'Token {evm_address} is not ERC20 conformant')  # noqa: E501  # pylint: disable=raise-missing-from

    elif token_kind == EvmTokenKind.ERC721:
        info = evm_inquirer.get_erc721_contract_info(evm_address)
        decimals = 0
        if symbol is None:
            symbol = info['symbol'] if info['symbol'] is not None else ''
        if name is None:
            name = info['name'] if info['name'] is not None else ''

    else:
        raise NotERC20Conformant(f'Token {evm_address} is of uknown type')  # pylint: disable=raise-missing-from  # noqa: E501

    return name, symbol, decimals


def _edit_token_and_clean_cache(
        evm_token: EvmToken,
        name: Optional[str],
        decimals: Optional[int],
        evm_inquirer: Optional['EvmNodeInquirer'],
) -> None:
    """
    Update information regarding name and decimals for an ethereum token.
    If name is missing in the database and is not provided then query the blockchain for it
    """
    updated_fields = False

    if evm_token.name == evm_token.identifier:
        if name is not None:
            object.__setattr__(evm_token, 'name', name)
            updated_fields = True
        elif evm_inquirer is not None:
            # query the chain for available information
            on_chain_name, _, on_chain_decimals = _query_or_get_given_token_info(
                evm_inquirer=evm_inquirer,
                evm_address=evm_token.evm_address,
                name=name,
                symbol=evm_token.symbol,
                decimals=decimals,
                token_kind=evm_token.token_kind,
            )
            object.__setattr__(evm_token, 'name', on_chain_name)
            object.__setattr__(evm_token, 'decimals', on_chain_decimals)
            updated_fields = True

    if decimals is not None and evm_token.decimals != decimals:
        object.__setattr__(evm_token, 'decimals', decimals)
        updated_fields = True

    # clean the cache if we need to update the token
    if updated_fields is True:
        AssetResolver.clean_memory_cache(evm_token.identifier)
        GlobalDBHandler().edit_evm_token(evm_token)


class TokenSeenAt(NamedTuple):
    tx_hash: Optional[EVMTxHash] = None
    description: Optional[str] = None


def get_or_create_evm_token(
        userdb: 'DBHandler',
        evm_address: ChecksumEvmAddress,
        chain_id: ChainID,
        token_kind: EvmTokenKind = EvmTokenKind.ERC20,
        symbol: Optional[str] = None,
        name: Optional[str] = None,
        decimals: Optional[int] = None,
        protocol: Optional[str] = None,
        underlying_tokens: Optional[list[UnderlyingToken]] = None,
        evm_inquirer: Optional['EvmNodeInquirer'] = None,
        seen: Optional[TokenSeenAt] = None,
) -> EvmToken:
    """Given a token address return the <EvmToken>

    If the token exists in the GlobalDB it's returned. If not it's created and added.

    If an ethereum_manager instance is passed then in the case that the token is not
    in the global DB it will be added and an attempt to get metadata will be made.

    Optionally the caller can provide a transaction hash of where the token was seen.
    This is used in the websocket message to provide information to the frontend.

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
        chain_id=chain_id,
        token_type=token_kind,
    )
    with userdb.get_or_create_evm_token_lock:
        try:
            evm_token = EvmToken(identifier=identifier)
            # It can happen that the asset is missing basic information but can be queried on
            # is provided by the developer. In that case make sure that no information
            # is cached and trigger the edit process.
            _edit_token_and_clean_cache(
                evm_token=evm_token,
                name=name,
                decimals=decimals,
                evm_inquirer=evm_inquirer,
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

            if evm_inquirer is not None:
                name, symbol, decimals = _query_or_get_given_token_info(
                    evm_inquirer=evm_inquirer,
                    evm_address=evm_address,
                    name=name,
                    symbol=symbol,
                    decimals=decimals,
                    token_kind=token_kind,
                )
            # make sure that basic information is always filled
            name = identifier if name is None else name
            decimals = 18 if decimals is None else decimals

            # Store the information in the database
            evm_token = EvmToken.initialize(
                address=evm_address,
                chain_id=chain_id,
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
                GlobalDBHandler().edit_evm_token(evm_token)
            else:
                # inform frontend new token detected
                data = {'token_identifier': identifier}
                if seen is not None:
                    if seen.tx_hash is not None:
                        data['seen_tx_hash'] = seen.tx_hash.hex()
                    else:  # description should have been given
                        data['seen_description'] = seen.description  # type: ignore
                userdb.msg_aggregator.add_message(
                    message_type=WSMessageType.NEW_EVM_TOKEN_DETECTED,
                    data=data,
                )
                # This can but should not raise InputError since it should not already exist.
                add_evm_token_to_db(token_data=evm_token)

                with userdb.user_write() as cursor:
                    userdb.add_asset_identifiers(cursor, [evm_token.identifier])

    return evm_token


def get_crypto_asset_by_symbol(
        symbol: str,
        asset_type: Optional[AssetType] = None,
        chain_id: Optional[ChainID] = None,
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
        chain_id=chain_id,
    )
    if len(assets_data) != 1:
        return None

    return assets_data[0]


def symbol_to_asset_or_token(
        symbol: str,
        chain_id: Optional[ChainID] = None,
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
        maybe_asset = get_crypto_asset_by_symbol(symbol=symbol, chain_id=chain_id)
        if maybe_asset is None:
            raise
        asset = maybe_asset

    return asset


def symbol_to_evm_token(symbol: str) -> EvmToken:
    """Tries to turn the given symbol to an evm token

    May raise:
    - UnknownAsset if an evm token can't be found by the symbol or if
    more than one tokens match this symbol
    """
    maybe_asset = get_crypto_asset_by_symbol(
        symbol=symbol,
        asset_type=AssetType.EVM_TOKEN,
        chain_id=ChainID.ETHEREUM,
    )
    if maybe_asset is None:
        raise UnknownAsset(symbol)

    return maybe_asset.resolve_to_evm_token()
