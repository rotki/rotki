import logging
from typing import TYPE_CHECKING, Any, Final, NamedTuple, Optional

import regex

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithOracles,
    EvmToken,
    SolanaToken,
    UnderlyingToken,
    WrongAssetType,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.assets import (
    A_ETH,
    A_WBNB,
    A_WETH,
    A_WETH_ARB,
    A_WETH_BASE,
    A_WETH_OPT,
    A_WETH_POLYGON,
    A_WETH_SCROLL,
    A_WXDAI,
)
from rotkehlchen.constants.resolver import evm_address_to_identifier, solana_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import NotERC20Conformant
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    EVM_TOKEN_KINDS,
    SOLANA_TOKEN_KINDS,
    SPAM_PROTOCOL,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    SolanaAddress,
    SupportedBlockchain,
    Timestamp,
    TokenKind,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SPAM_ASSET_REGEX = r"""
    https:// |                      # Matches 'https://'
    claim | visit | invited |       # Matches 'claim' or 'visit' anywhere in the string
    ^\$.+\..+ |                     # Matches strings that start with '$' and contain '.'
    (\p{Sk}|\p{Po})+(com|io|site|xyz|li|org|cc|net|pm)+  # Matches common domain extensions. It also detects any letter modifier or punctuation in unicode before the domain extension
"""  # noqa: E501
# Compile the regex pattern:
# - re.IGNORECASE makes it case-insensitive
# - re.VERBOSE allows to write comments in the regex and split it
SPAM_ASSET_PATTERN = regex.compile(SPAM_ASSET_REGEX, regex.IGNORECASE | regex.VERBOSE)


def add_evm_token_to_db(token_data: EvmToken) -> EvmToken:
    """Adds an evm token to the DB and returns it

    May raise:
    - InputError if token already exists in the DB
    """
    GlobalDBHandler.add_asset(token_data)
    # This can, but should not raise UnknownAsset, DeserializationError
    return EvmToken(token_data.identifier)


def _query_or_get_given_token_info(
        evm_inquirer: 'EvmNodeInquirer',
        evm_address: ChecksumEvmAddress,
        name: str | None,
        symbol: str | None,
        decimals: int | None,
        token_kind: EVM_TOKEN_KINDS,
) -> tuple[str | None, str | None, int | None]:
    """
    Query ethereum to retrieve basic contract information for the given address.
    If the contract is missing any of the queried methods then the respective value
    given as parameter to this function is used.
    May raise:
    - NotERC20Conformant
    """
    if token_kind == TokenKind.ERC20:
        info = evm_inquirer.get_erc20_contract_info(evm_address)
        decimals = info['decimals'] if decimals is None else decimals
        symbol = info['symbol'] if symbol is None else symbol
        name = info['name'] if name is None else name
        if None in (decimals, symbol, name):
            raise NotERC20Conformant(f'Token {evm_address} is not ERC20 conformant')  # pylint: disable=raise-missing-from

    elif token_kind == TokenKind.ERC721:
        info = evm_inquirer.get_erc721_contract_info(evm_address)
        decimals = 0
        if symbol is None:
            symbol = info['symbol'] if info['symbol'] is not None else ''
        if name is None:
            name = info['name'] if info['name'] is not None else ''

    else:
        raise NotERC20Conformant(f'Token {evm_address} is of unknown type')  # pylint: disable=raise-missing-from

    return name, symbol, decimals


def edit_token_and_clean_cache(
        evm_token: EvmToken,
        name: str | None,
        symbol: str | None,
        decimals: int | None,
        started: Timestamp | None,
        underlying_tokens: list[UnderlyingToken] | None,
        evm_inquirer: 'EvmNodeInquirer | None',
        coingecko: str | None = None,
        cryptocompare: str | None = None,
        protocol: str | None = None,
) -> None:
    """
    Update information regarding name and decimals for an ethereum token.
    If name is missing in the database and is not provided then query the blockchain for it
    May raise:
        - InputError if there is an error while editing the token
    """
    updated_fields = False

    if name is not None and evm_token.name != name:
        object.__setattr__(evm_token, 'name', name)
        updated_fields = True
    elif evm_token.name == evm_token.identifier and evm_inquirer is not None:
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

    if symbol is not None and evm_token.symbol != symbol:
        object.__setattr__(evm_token, 'symbol', symbol)
        updated_fields = True

    if decimals is not None and evm_token.decimals != decimals:
        object.__setattr__(evm_token, 'decimals', decimals)
        updated_fields = True

    if started is not None and evm_token.started != started:
        object.__setattr__(evm_token, 'started', started)
        updated_fields = True

    if underlying_tokens is not None and evm_token.underlying_tokens != underlying_tokens:
        object.__setattr__(evm_token, 'underlying_tokens', underlying_tokens)
        updated_fields = True

    if coingecko is not None and evm_token.coingecko != coingecko:
        object.__setattr__(evm_token, 'coingecko', coingecko)
        updated_fields = True

    if cryptocompare is not None and evm_token.cryptocompare != cryptocompare:
        object.__setattr__(evm_token, 'cryptocompare', cryptocompare)
        updated_fields = True

    if protocol is not None and evm_token.protocol != protocol:
        object.__setattr__(evm_token, 'protocol', protocol)
        updated_fields = True

    # clean the cache if we need to update the token
    if updated_fields is True:
        GlobalDBHandler.edit_evm_token(evm_token)


def check_if_spam_token(symbol: str | None, name: str | None) -> bool:
    """Makes basic checks to test if a token could be spam or not"""
    if symbol is None and name is None:
        return False

    if (
        symbol is not None and
        SPAM_ASSET_PATTERN.search(symbol) is not None
    ):
        return True

    if name is None:
        return False

    # check also the name
    return SPAM_ASSET_PATTERN.search(name) is not None


class TokenEncounterInfo(NamedTuple):
    """
    Information that will be provided to the user when adding new assets.

    If should_notify is True then we will send a ws message with information
    about the new asset
    """
    tx_hash: EVMTxHash | None = None
    description: str | None = None
    should_notify: bool = True


def get_evm_token(
        evm_address: ChecksumEvmAddress,
        chain_id: ChainID,
        token_kind: EVM_TOKEN_KINDS = TokenKind.ERC20,
        collectible_id: str | None = None,
) -> EvmToken | None:
    """Query an EVM token from the cache of the AssetResolver or the GlobalDB if
    it is not in the cache. If the token doesn't exist this function returns None.
    """
    identifier = evm_address_to_identifier(
        address=evm_address,
        chain_id=chain_id,
        token_type=token_kind,
        collectible_id=collectible_id,
    )
    try:
        return AssetResolver.resolve_asset_to_class(
            identifier=identifier,
            expected_type=EvmToken,
        )
    except (UnknownAsset, WrongAssetType):
        return None


def get_solana_token(
        address: SolanaAddress,
        token_kind: SOLANA_TOKEN_KINDS | None = None,
) -> SolanaToken | None:
    """Query a solana token from the cache of the AssetResolver or the GlobalDB if
    it is not in the cache. If the token_kind isn't specified, both types will be tried to allow
    loading both tokens and nfts from only a token address.
    Returns the token or None if the token doesn't exist.
    """
    for token_type in (TokenKind.SPL_TOKEN, TokenKind.SPL_NFT) if token_kind is None else (token_kind,):  # noqa: E501
        try:
            return Asset(solana_address_to_identifier(
                address=address,
                token_type=token_type,
            )).resolve_to_solana_token()
        except (UnknownAsset, WrongAssetType):
            continue

    return None


def get_single_underlying_token(token: 'EvmToken') -> 'EvmToken | None':
    """Get a token's single underlying token.
    Returns the underlying token or None if the token has no/multiple underlying tokens.
    """
    if (
        token.underlying_tokens is not None and
        len(token.underlying_tokens) == 1 and
        (underlying_token := get_evm_token(
            evm_address=token.underlying_tokens[0].address,
            chain_id=token.chain_id,
        )) is not None
    ):
        return underlying_token

    return None


def get_or_create_evm_token(
        userdb: 'DBHandler',
        evm_address: ChecksumEvmAddress,
        chain_id: ChainID,
        token_kind: EVM_TOKEN_KINDS = TokenKind.ERC20,
        symbol: str | None = None,
        name: str | None = None,
        decimals: int | None = None,
        protocol: str | None = None,
        started: Timestamp | None = None,
        underlying_tokens: list[UnderlyingToken] | None = None,
        evm_inquirer: Optional['EvmNodeInquirer'] = None,
        encounter: TokenEncounterInfo | None = None,
        coingecko: str | None = None,
        cryptocompare: str | None = None,
        fallback_decimals: int | None = None,
        fallback_name: str | None = None,
        fallback_symbol: str | None = None,
        collectible_id: str | None = None,
) -> EvmToken:
    """Given a token address return the <EvmToken>

    If the token exists in the GlobalDB it's returned. If not it's created and added.

    If an ethereum_manager instance is passed then in the case that the token is not
    in the global DB it will be added and an attempt to get metadata will be made.

    Optionally the caller can provide a transaction hash of where the token was seen.
    This is used in the websocket message to provide information to the frontend.

    If fallback values are provided and the token isn't ERC20 conformant we use those
    as values for the decimal, name and symbol attributes.

    Note: if the token already exists but the other arguments don't match the
    existing token will still be silently returned
    Note2: This entire function is designed so that it does not context switch away from
    its calling greenlet so it should be safe to call from multiple greenlets.
    Note3: If encounter is None, it will broadcast the `NEW_EVM_TOKEN_DETECTED` message by default.

    May raise:
    - NotERC20Conformant exception if an ethereum manager is given to query
    and the given address does not have any of symbol, decimals and name
    - NotERC721Conformant exception if an ethereum manager is given to query
    and the given address does not conform to ERC721 spec
    - InputError if there is an error while editing the token
    """
    identifier = evm_address_to_identifier(
        address=evm_address,
        chain_id=chain_id,
        token_type=token_kind,
        collectible_id=collectible_id,
    )
    with userdb.get_or_create_evm_token_lock:
        try:
            evm_token = EvmToken(identifier=identifier)
            # It can happen that the asset is missing basic information but can be queried on
            # is provided by the developer. In that case make sure that no information
            # is cached and trigger the edit process.
            edit_token_and_clean_cache(
                evm_token=evm_token,
                name=name,
                symbol=symbol,
                decimals=decimals,
                started=started,
                underlying_tokens=underlying_tokens,
                evm_inquirer=evm_inquirer,
                coingecko=coingecko,
                cryptocompare=cryptocompare,
                protocol=protocol,
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

            if (
                None in (name, symbol, decimals) and
                evm_inquirer is not None
            ):
                try:
                    name, symbol, decimals = _query_or_get_given_token_info(
                        evm_inquirer=evm_inquirer,
                        evm_address=evm_address,
                        name=name,
                        symbol=symbol,
                        decimals=decimals,
                        token_kind=token_kind,
                    )
                except NotERC20Conformant:
                    if None not in (fallback_name, fallback_symbol, fallback_decimals):
                        name, symbol, decimals = fallback_name, fallback_symbol, fallback_decimals
                    else:
                        raise

            # make sure that basic information is always filled
            name = identifier if name is None else name
            decimals = 18 if decimals is None else decimals

            is_spam_token = (
                protocol == SPAM_PROTOCOL or
                (protocol is None and check_if_spam_token(symbol=symbol, name=name))
            )

            # Store the information in the database
            evm_token = EvmToken.initialize(
                address=evm_address,
                chain_id=chain_id,
                token_kind=token_kind,
                name=name,
                decimals=decimals,
                symbol=symbol,
                protocol=protocol if not is_spam_token else SPAM_PROTOCOL,
                underlying_tokens=underlying_tokens,
                started=started,
                coingecko=coingecko,
                cryptocompare=cryptocompare,
                collectible_id=collectible_id,
            )
            if asset_exists is True:
                # This means that we need to update the information in the database with the
                # newly queried data
                GlobalDBHandler.edit_evm_token(evm_token)
            else:
                # inform frontend new token detected
                data: dict[str, Any] = {'token_identifier': identifier}
                if is_spam_token:
                    data['is_ignored'] = True

                if (should_notify := encounter is not None and encounter.should_notify):
                    if encounter.tx_hash is not None:
                        data['seen_tx_hash'] = encounter.tx_hash.hex()
                    else:  # description should have been given
                        data['seen_description'] = encounter.description

                if encounter is None or should_notify:
                    userdb.msg_aggregator.add_message(
                        message_type=WSMessageType.NEW_EVM_TOKEN_DETECTED,
                        data=data,
                    )
                # This can but should not raise InputError since it should not already exist.
                add_evm_token_to_db(token_data=evm_token)

                with userdb.user_write() as write_cursor:
                    userdb.add_asset_identifiers(write_cursor, [evm_token.identifier])
                    # at this point the newly detected asset has just been added to the DB
                    if is_spam_token:
                        userdb.add_to_ignored_assets(write_cursor=write_cursor, asset=evm_token)

    return evm_token


def get_crypto_asset_by_symbol(
        symbol: str,
        asset_type: AssetType | None = None,
        chain_id: ChainID | None = None,
) -> AssetWithOracles | None:
    """Gets an asset by symbol from the DB.

    If no asset with that symbol or multiple assets (except for EVM tokens) with the same
    symbol are found returns None. If all the results are evm tokens then the one from the
    preferred_chain is selected.
    """
    if symbol == 'ETH':
        return A_ETH.resolve_to_asset_with_oracles()  # ETH can be ETH and ETH2 in the DB

    assets_data = GlobalDBHandler.get_assets_with_symbol(
        symbol=symbol,
        asset_type=asset_type,
        chain_id=chain_id,
    )
    if len(assets_data) != 1:
        return None

    return assets_data[0]


def symbol_to_asset_or_token(
        symbol: str,
        chain_id: ChainID | None = None,
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


CHAIN_TO_WRAPPED_TOKEN: Final = {
    SupportedBlockchain.ETHEREUM: A_WETH,
    SupportedBlockchain.ARBITRUM_ONE: A_WETH_ARB,
    SupportedBlockchain.OPTIMISM: A_WETH_OPT,
    SupportedBlockchain.BASE: A_WETH_BASE,
    SupportedBlockchain.GNOSIS: A_WXDAI,
    SupportedBlockchain.POLYGON_POS: A_WETH_POLYGON,
    SupportedBlockchain.BINANCE_SC: A_WBNB,
    SupportedBlockchain.SCROLL: A_WETH_SCROLL,
}
