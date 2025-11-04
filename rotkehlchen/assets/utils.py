import logging
from collections.abc import Callable
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Final, NamedTuple, overload

import regex
from solders.solders import Signature

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithOracles,
    CryptoAsset,
    EvmToken,
    SolanaToken,
    UnderlyingToken,
    WrongAssetType,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetType
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.solana.utils import is_solana_token_nft
from rotkehlchen.constants.assets import (
    A_BSC_BNB,
    A_ETH,
    A_WBNB,
    A_WETH,
    A_WETH_ARB,
    A_WETH_BASE,
    A_WETH_OPT,
    A_WETH_SCROLL,
    A_WPOL,
    A_WXDAI,
    A_XDAI,
)
from rotkehlchen.constants.resolver import evm_address_to_identifier, solana_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant, NotSPLConformant
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    EVM_TOKEN_KINDS,
    EVM_TOKEN_KINDS_TYPE,
    SOLANA_TOKEN_KINDS_TYPE,
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
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
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


def _query_or_get_given_token_info(
        chain_inquirer: 'EvmNodeInquirer | SolanaInquirer',
        address: ChecksumEvmAddress | SolanaAddress,
        name: str | None,
        symbol: str | None,
        decimals: int | None,
        token_kind: EVM_TOKEN_KINDS_TYPE | SOLANA_TOKEN_KINDS_TYPE | None,
) -> tuple[str | None, str | None, int | None, EVM_TOKEN_KINDS_TYPE | SOLANA_TOKEN_KINDS_TYPE | None]:  # noqa: E501
    """Query basic token information for the given address.
    If unable to get the values from onchain data then the values given as arguments are used.
    Returns the name, symbol and decimals in a tuple.
    """
    if token_kind in EVM_TOKEN_KINDS:
        if token_kind == TokenKind.ERC20:
            with suppress(NotERC20Conformant):
                info = chain_inquirer.get_erc20_contract_info(address)  # type: ignore
                decimals = info['decimals'] if decimals is None else decimals
                symbol = info['symbol'] if symbol is None else symbol
                name = info['name'] if name is None else name

        else:  # TokenKind.ERC721
            with suppress(NotERC721Conformant):
                info = chain_inquirer.get_erc721_contract_info(address)  # type: ignore
                decimals = 0
                symbol = info['symbol'] or '' if symbol is None else symbol
                name = info['name'] or '' if name is None else name

    elif (  # Solana token kinds
        (decimals is None or name is None or symbol is None) and  # don't query if we have all the data already  # noqa: E501
        (mint_info := chain_inquirer.get_token_mint_info(address)) is not None  # type: ignore
    ):
        decimals = decimals or mint_info.decimals

        if (
            (name is None or symbol is None) and
            (metadata := chain_inquirer.get_token_metadata(token_address=address, mint_info=mint_info)) is not None  # type: ignore  # noqa: E501
        ):
            name = name or metadata.name
            symbol = symbol or metadata.symbol
            if token_kind is None:
                token_kind = TokenKind.SPL_NFT if is_solana_token_nft(
                    token_address=address,  # type: ignore[arg-type]
                    mint_info=mint_info,
                    metadata=metadata,
                ) else TokenKind.SPL_TOKEN

    return name, symbol, decimals, token_kind


def edit_token_and_clean_cache(
        token: EvmToken | SolanaToken,
        name: str | None,
        symbol: str | None,
        decimals: int | None,
        started: Timestamp | None,
        chain_inquirer: 'EvmNodeInquirer | SolanaInquirer | None',
        underlying_tokens: list[UnderlyingToken] | None = None,
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

    if name is not None and token.name != name:
        object.__setattr__(token, 'name', name)
        updated_fields = True
    elif token.name == token.identifier and chain_inquirer is not None:
        # query the chain for available information
        on_chain_name, on_chain_symbol, on_chain_decimals, _ = _query_or_get_given_token_info(
            chain_inquirer=chain_inquirer,
            address=token.evm_address if isinstance(token, EvmToken) else token.mint_address,
            name=name,
            symbol=symbol,
            decimals=decimals,
            token_kind=token.token_kind,
        )
        object.__setattr__(token, 'name', on_chain_name)
        object.__setattr__(token, 'symbol', on_chain_symbol)
        object.__setattr__(token, 'decimals', on_chain_decimals)
        updated_fields = True

    if symbol is not None and token.symbol != symbol:
        object.__setattr__(token, 'symbol', symbol)
        updated_fields = True

    if decimals is not None and token.decimals != decimals:
        object.__setattr__(token, 'decimals', decimals)
        updated_fields = True

    if started is not None and token.started != started:
        object.__setattr__(token, 'started', started)
        updated_fields = True

    if (
        underlying_tokens is not None and
        isinstance(token, EvmToken) and
        token.underlying_tokens != underlying_tokens
    ):
        object.__setattr__(token, 'underlying_tokens', underlying_tokens)
        updated_fields = True

    if coingecko is not None and token.coingecko != coingecko:
        object.__setattr__(token, 'coingecko', coingecko)
        updated_fields = True

    if cryptocompare is not None and token.cryptocompare != cryptocompare:
        object.__setattr__(token, 'cryptocompare', cryptocompare)
        updated_fields = True

    if protocol is not None and token.protocol != protocol:
        object.__setattr__(token, 'protocol', protocol)
        updated_fields = True

    # clean the cache if we need to update the token
    if updated_fields is True:
        if isinstance(token, EvmToken):
            GlobalDBHandler.edit_evm_token(token)
        else:
            GlobalDBHandler.edit_solana_token(token)


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
    tx_ref: EVMTxHash | Signature | None = None
    description: str | None = None
    should_notify: bool = True


def get_evm_token(
        evm_address: ChecksumEvmAddress,
        chain_id: ChainID,
        token_kind: EVM_TOKEN_KINDS_TYPE = TokenKind.ERC20,
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
        token_kind: SOLANA_TOKEN_KINDS_TYPE | None = None,
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
        token_kind: EVM_TOKEN_KINDS_TYPE = TokenKind.ERC20,
        symbol: str | None = None,
        name: str | None = None,
        decimals: int | None = None,
        protocol: str | None = None,
        started: Timestamp | None = None,
        underlying_tokens: list[UnderlyingToken] | None = None,
        evm_inquirer: 'EvmNodeInquirer | None' = None,
        encounter: TokenEncounterInfo | None = None,
        coingecko: str | None = None,
        cryptocompare: str | None = None,
        fallback_decimals: int | None = None,
        fallback_name: str | None = None,
        fallback_symbol: str | None = None,
        collectible_id: str | None = None,
) -> EvmToken:
    """Given a token address return the EvmToken.
    Wrapper around _get_or_create_token that handles getting the EVM token identifier.
    """
    return _get_or_create_token(
        userdb=userdb,
        identifier=evm_address_to_identifier(
            address=evm_address,
            chain_id=chain_id,
            token_type=token_kind,
            collectible_id=collectible_id,
        ),
        address=evm_address,
        token_class=EvmToken,
        edit_token_fn=GlobalDBHandler.edit_evm_token,
        token_kind=token_kind,
        chain_id=chain_id,
        symbol=symbol,
        name=name,
        decimals=decimals,
        protocol=protocol,
        started=started,
        underlying_tokens=underlying_tokens,
        chain_inquirer=evm_inquirer,
        encounter=encounter,
        coingecko=coingecko,
        cryptocompare=cryptocompare,
        fallback_decimals=fallback_decimals,
        fallback_name=fallback_name,
        fallback_symbol=fallback_symbol,
        collectible_id=collectible_id,
    )


def get_or_create_solana_token(
        userdb: 'DBHandler',
        address: SolanaAddress,
        token_kind: SOLANA_TOKEN_KINDS_TYPE | None = None,
        symbol: str | None = None,
        name: str | None = None,
        decimals: int | None = None,
        protocol: str | None = None,
        started: Timestamp | None = None,
        solana_inquirer: 'SolanaInquirer | None' = None,
        encounter: TokenEncounterInfo | None = None,
        coingecko: str | None = None,
        cryptocompare: str | None = None,
        fallback_decimals: int | None = None,
        fallback_name: str | None = None,
        fallback_symbol: str | None = None,
) -> SolanaToken:
    """Given a token address return the SolanaToken.

    Wrapper around _get_or_create_token that handles getting the identifier.
    If token_kind is specified, the correct identifier for that token kind will be generated,
    but if token_kind is None, then it will attempt to load either a token or an nft with this
    address from the db. If that fails, then the identifier is set to None and will need to be
    determined from onchain data.

    May raise NotSPLConformant if unable to load an SPL token/nft for the given address.
    Note that this will always raise if both `solana_inquirer` and `token_kind` are None and the
    token is not in the DB.
    """
    if token_kind is not None:
        identifier = solana_address_to_identifier(address=address, token_type=token_kind)
    else:  # Attempt to load either a token or nft with this address from the db
        for kind in (TokenKind.SPL_TOKEN, TokenKind.SPL_NFT):
            try:
                if Asset(identifier := solana_address_to_identifier(
                    address=address,
                    token_type=kind,
                )).check_existence() is not None:
                    break
            except UnknownAsset:
                continue
        else:  # Otherwise we don't know if this is a token or nft without querying the chain and can't say what the identifier is.  # noqa: E501
            identifier = None

    return _get_or_create_token(
        userdb=userdb,
        identifier=identifier,
        address=address,
        token_class=SolanaToken,
        edit_token_fn=GlobalDBHandler.edit_solana_token,
        token_kind=token_kind,
        symbol=symbol,
        name=name,
        decimals=decimals,
        protocol=protocol,
        started=started,
        chain_inquirer=solana_inquirer,
        encounter=encounter,
        coingecko=coingecko,
        cryptocompare=cryptocompare,
        fallback_decimals=fallback_decimals,
        fallback_name=fallback_name,
        fallback_symbol=fallback_symbol,
    )


@overload
def _get_or_create_token(
        userdb: 'DBHandler',
        identifier: str,
        address: ChecksumEvmAddress,
        token_class: type[EvmToken],
        edit_token_fn: Callable[['EvmToken'], str],
        token_kind: EVM_TOKEN_KINDS_TYPE,
        chain_id: ChainID,
        symbol: str | None = None,
        name: str | None = None,
        decimals: int | None = None,
        protocol: str | None = None,
        started: Timestamp | None = None,
        underlying_tokens: list[UnderlyingToken] | None = None,
        chain_inquirer: 'EvmNodeInquirer | None' = None,
        encounter: TokenEncounterInfo | None = None,
        coingecko: str | None = None,
        cryptocompare: str | None = None,
        fallback_decimals: int | None = None,
        fallback_name: str | None = None,
        fallback_symbol: str | None = None,
        collectible_id: str | None = None,
) -> EvmToken:
    ...


@overload
def _get_or_create_token(
        userdb: 'DBHandler',
        identifier: str | None,
        address: SolanaAddress,
        token_class: type[SolanaToken],
        edit_token_fn: Callable[['SolanaToken'], str],
        token_kind: SOLANA_TOKEN_KINDS_TYPE | None = None,
        chain_id: None = None,
        symbol: str | None = None,
        name: str | None = None,
        decimals: int | None = None,
        protocol: str | None = None,
        started: Timestamp | None = None,
        underlying_tokens: list[UnderlyingToken] | None = None,
        chain_inquirer: 'SolanaInquirer | None' = None,
        encounter: TokenEncounterInfo | None = None,
        coingecko: str | None = None,
        cryptocompare: str | None = None,
        fallback_decimals: int | None = None,
        fallback_name: str | None = None,
        fallback_symbol: str | None = None,
) -> SolanaToken:
    ...


def _get_or_create_token(
        userdb: 'DBHandler',
        identifier: str | None,
        address: ChecksumEvmAddress | SolanaAddress,
        token_class: type[EvmToken] | type[SolanaToken],
        edit_token_fn: Callable[['EvmToken'], str] | Callable[['SolanaToken'], str],
        token_kind: EVM_TOKEN_KINDS_TYPE | SOLANA_TOKEN_KINDS_TYPE | None = None,
        chain_id: ChainID | None = None,
        symbol: str | None = None,
        name: str | None = None,
        decimals: int | None = None,
        protocol: str | None = None,
        started: Timestamp | None = None,
        underlying_tokens: list[UnderlyingToken] | None = None,
        chain_inquirer: 'EvmNodeInquirer | SolanaInquirer | None' = None,
        encounter: TokenEncounterInfo | None = None,
        coingecko: str | None = None,
        cryptocompare: str | None = None,
        fallback_decimals: int | None = None,
        fallback_name: str | None = None,
        fallback_symbol: str | None = None,
        collectible_id: str | None = None,
) -> EvmToken | SolanaToken:
    """Given a token address return the EvmToken or SolanaToken.

    If the token exists in the GlobalDB it's returned. If not it's created and added.

    If a chain_manager instance is passed, then in the case that the token is not
    in the global DB it will be added and an attempt to get metadata will be made.

    Optionally the caller can provide encounter info with a tx hash of where the token was seen.
    This is used in the websocket message to provide information to the frontend.

    If fallback values are provided and the token isn't ERC20/ERC721/SPL conformant we use those
    as values for the decimal, name and symbol attributes.

    Note: if the token already exists but the other arguments don't match the
    existing token will still be silently returned
    Note2: This entire function is designed so that it does not context switch away from
    its calling greenlet so it should be safe to call from multiple greenlets.
    Note3: If encounter is None, it will broadcast the `NEW_TOKEN_DETECTED` message by default.

    May raise:
    - NotERC20Conformant if token_kind is ERC20 and a chain_inquirer is given but the given
       address does not conform to the ERC20 spec
    - NotERC721Conformant if token_kind is ERC721 and a chain_inquirer is given but the given
       address does not conform to the ERC721 spec
    - NotSPLConformant in two cases:
        * if token_kind is SPL_TOKEN or SPL_NFT and a chain_inquirer is given but the token info
          couldn't be queried from onchain
        * if both token_kind and chain_inquirer are None and the token is not in the DB.
    - InputError if there is an error while editing the token
    """
    with userdb.get_or_create_token_lock:
        if identifier is not None:
            try:  # Attempt to edit the (possibly) existing token using the provided arguments.
                edit_token_and_clean_cache(
                    token=(token := token_class(identifier)),
                    name=name,
                    symbol=symbol,
                    decimals=decimals,
                    started=started,
                    underlying_tokens=underlying_tokens,
                    chain_inquirer=chain_inquirer,
                    coingecko=coingecko,
                    cryptocompare=cryptocompare,
                    protocol=protocol,
                )
            except (UnknownAsset, DeserializationError):
                try:  # It can happen that the asset exists but is missing basic information.
                    asset_exists = Asset(identifier).check_existence() is not None
                except UnknownAsset:
                    asset_exists = False
            else:
                return token
        else:
            asset_exists = False

        if None in (name, symbol, decimals, token_kind) and chain_inquirer is not None:
            name, symbol, decimals, token_kind = _query_or_get_given_token_info(
                chain_inquirer=chain_inquirer,
                address=address,
                name=name,
                symbol=symbol,
                decimals=decimals,
                token_kind=token_kind,
            )

            if (
                    (missing_metadata := None in (name, symbol, decimals, token_kind)) and
                    None not in (fallback_name, fallback_symbol, fallback_decimals)
            ):
                name, symbol, decimals = fallback_name, fallback_symbol, fallback_decimals
            elif missing_metadata:
                raise (
                    NotERC20Conformant(f'Token {address} is not ERC20 conformant')
                    if token_kind == TokenKind.ERC20 else
                    NotERC721Conformant(f'Token {address} is not ERC721 conformant')
                    if token_kind == TokenKind.ERC721 else
                    NotSPLConformant(f'Token {address} is not SPL conformant')
                )

        # token_kind and identifier will only be None here if we are processing a solana token
        if token_kind is None:
            raise NotSPLConformant(f'Token {address} is not SPL conformant')
        if identifier is None:
            identifier = solana_address_to_identifier(address=address, token_type=token_kind)  # type: ignore[arg-type]

        # make sure that basic information is always filled
        name = identifier if name is None else name
        # only evm tokens are missing decimals here.
        decimals = DEFAULT_TOKEN_DECIMALS if decimals is None else decimals

        is_spam_token = (
            protocol == SPAM_PROTOCOL or
            (protocol is None and check_if_spam_token(symbol=symbol, name=name))
        )

        token_kwargs = {
            'address': address,
            'token_kind': token_kind,
            'name': name,
            'decimals': decimals,
            'symbol': symbol,
            'protocol': protocol if not is_spam_token else SPAM_PROTOCOL,
            'started': started,
            'coingecko': coingecko,
            'cryptocompare': cryptocompare,
        }
        if token_class == EvmToken:
            token_kwargs.update({
                'chain_id': chain_id,  # type: ignore[dict-item]
                'collectible_id': collectible_id,
                'underlying_tokens': underlying_tokens,  # type: ignore[dict-item]
            })

        # Store the information in the database
        token = token_class.initialize(**token_kwargs)  # type: ignore[arg-type]
        if asset_exists is True:
            # This means that we need to update the information in the database with the
            # newly queried data
            edit_token_fn(token)  # type: ignore[arg-type]  # can only be one of evm/solana
        else:
            if encounter is None or encounter.should_notify:
                # inform the frontend that a new token was detected
                data: dict[str, Any] = {
                    'token_identifier': identifier,
                    'token_kind': 'evm' if token_class == EvmToken else 'solana',
                }
                if is_spam_token:
                    data['is_ignored'] = True
                if encounter is not None:
                    if encounter.tx_ref is not None:
                        data['seen_tx_reference'] = str(encounter.tx_ref)
                    else:  # description should have been given
                        data['seen_description'] = encounter.description

                userdb.msg_aggregator.add_message(
                    message_type=WSMessageType.NEW_TOKEN_DETECTED,
                    data=data,
                )
            # This can but should not raise InputError since it should not already exist.
            GlobalDBHandler.add_asset(token)
            # This can, but should not raise UnknownAsset, DeserializationError
            token = token_class(token.identifier)

            with userdb.user_write() as write_cursor:
                userdb.add_asset_identifiers(write_cursor, [token.identifier])
                # at this point the newly detected asset has just been added to the DB
                if is_spam_token:
                    userdb.add_to_ignored_assets(write_cursor=write_cursor, asset=token)

    return token


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


def token_normalized_value_decimals(token_amount: int, token_decimals: int | None) -> FVal:
    if token_decimals is None:  # if somehow no info on decimals ends up here assume 18
        token_decimals = 18

    return token_amount / (FVal(10) ** FVal(token_decimals))


def normalized_fval_value_decimals(amount: FVal, decimals: int) -> FVal:
    return amount / (FVal(10) ** FVal(decimals))


def token_raw_value_decimals(token_amount: FVal, token_decimals: int | None) -> int:
    if token_decimals is None:  # if somehow no info on decimals ends up here assume 18
        token_decimals = 18

    return (token_amount * (FVal(10) ** FVal(token_decimals))).to_int(exact=False)


def token_normalized_value(
        token_amount: int,
        token: EvmToken | SolanaToken,
) -> FVal:
    return token_normalized_value_decimals(token_amount, token.decimals)


def get_decimals(asset: CryptoAsset) -> int:
    """
    May raise:
    - UnsupportedAsset if the given asset is not a native token or an ERC20 token
    """
    if asset in (A_ETH, A_XDAI, A_BSC_BNB):
        return 18
    try:
        token = asset.resolve_to_evm_token()
    except UnknownAsset as e:
        raise UnsupportedAsset(asset.identifier) from e

    return token.get_decimals()


def asset_normalized_value(amount: int, asset: CryptoAsset) -> FVal:
    """Takes in an amount and an asset and returns its normalized value

    May raise:
    - UnsupportedAsset if the given asset is not ETH or an ethereum token
    """
    return token_normalized_value_decimals(amount, get_decimals(asset))


def asset_raw_value(amount: FVal, asset: CryptoAsset) -> int:
    """Takes in an amount and an asset and returns its raw(wei equivalent) value

    May raise:
    - UnsupportedAsset if the given asset is not ETH or an ethereum token
    """
    return token_raw_value_decimals(amount, get_decimals(asset))


CHAIN_TO_WRAPPED_TOKEN: Final = {
    SupportedBlockchain.ETHEREUM: A_WETH,
    SupportedBlockchain.ARBITRUM_ONE: A_WETH_ARB,
    SupportedBlockchain.OPTIMISM: A_WETH_OPT,
    SupportedBlockchain.BASE: A_WETH_BASE,
    SupportedBlockchain.GNOSIS: A_WXDAI,
    SupportedBlockchain.POLYGON_POS: A_WPOL,
    SupportedBlockchain.BINANCE_SC: A_WBNB,
    SupportedBlockchain.SCROLL: A_WETH_SCROLL,
}
