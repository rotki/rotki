import logging
from typing import TYPE_CHECKING, Any, Dict, Literal, Tuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_evm_address,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    EVMTxHash,
    Price,
    deserialize_evm_tx_hash,
)

from .types import (
    BalancerBPTEvent,
    BalancerBPTEventType,
    BalancerInvestEvent,
    BalancerInvestEventType,
    BalancerPoolBalance,
    BalancerPoolTokenBalance,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

UNISWAP_REMOTE_ERROR_MSG = (
    "Could not initialize the Uniswap subgraph due to {error_msg}. "
    "All Balancer balances and historical queries won't be able to use a "
    "secondary price oracle for requesting the USD price of the unsupported tokens. "
    "Probably will get fixed with time. If not report it to rotki's support channel"
)


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def deserialize_bpt_event(
        userdb: 'DBHandler',
        raw_event: Dict[str, Any],
        event_type: Literal[BalancerBPTEventType.MINT, BalancerBPTEventType.BURN],
) -> BalancerBPTEvent:
    """May raise DeserializationError"""
    try:
        tx_hash, log_index = deserialize_transaction_id(raw_event['id'])
        raw_user_address = raw_event['user']['id']
        amount = deserialize_asset_amount(raw_event['amount'])
        raw_pool = raw_event['pool']
        raw_pool_address = raw_pool['id']
        raw_pool_tokens = raw_pool['tokens']
        total_weight = deserialize_asset_amount(raw_pool['totalWeight'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    if total_weight == ZERO:
        raise DeserializationError('Pool weight is zero.')

    user_address = deserialize_evm_address(raw_user_address)
    pool_address = deserialize_evm_address(raw_pool_address)

    underlying_tokens = []
    for raw_token in raw_pool_tokens:
        try:
            raw_token_address = raw_token['address']
            token_symbol = raw_token['symbol']
            token_name = raw_token['name']
            token_decimals = raw_token['decimals']
            token_weight = deserialize_asset_amount(raw_token['denormWeight'])
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        token_address = deserialize_evm_address(raw_token_address)

        token = get_or_create_evm_token(
            userdb=userdb,
            symbol=token_symbol,
            evm_address=token_address,
            chain=ChainID.ETHEREUM,
            name=token_name,
            decimals=token_decimals,
        )
        underlying_tokens.append(UnderlyingToken(
            address=token.evm_address,
            token_kind=EvmTokenKind.ERC20,
            weight=token_weight / total_weight,
        ))

    underlying_tokens.sort(key=lambda x: x.address)
    pool_address_token = get_or_create_evm_token(
        userdb=userdb,
        evm_address=pool_address,
        chain=ChainID.ETHEREUM,
        symbol='BPT',
        protocol='balancer',
        decimals=18,  # all BPT tokens have 18 decimals
        underlying_tokens=underlying_tokens,
        form_with_incomplete_data=True,  # since some may not have decimals input correctly
    )
    bpt_event = BalancerBPTEvent(
        tx_hash=tx_hash,
        log_index=log_index,
        address=user_address,
        event_type=event_type,
        pool_address_token=pool_address_token,
        amount=amount,
    )
    return bpt_event


def deserialize_invest_event(
        raw_event: Dict[str, Any],
        event_type: Literal[
            BalancerInvestEventType.ADD_LIQUIDITY,
            BalancerInvestEventType.REMOVE_LIQUIDITY,
        ],
) -> BalancerInvestEvent:
    """May raise DeserializationError"""
    try:
        tx_hash, log_index = deserialize_transaction_id(raw_event['id'])
        timestamp = deserialize_timestamp(raw_event['timestamp'])
        raw_user_address = raw_event['userAddress']['id']
        raw_pool_address = raw_event['poolAddress']['id']
        if event_type == BalancerInvestEventType.ADD_LIQUIDITY:
            raw_token_address = raw_event['tokenIn']['address']
            amount = deserialize_asset_amount(raw_event['tokenAmountIn'])
        elif event_type == BalancerInvestEventType.REMOVE_LIQUIDITY:
            raw_token_address = raw_event['tokenOut']['address']
            amount = deserialize_asset_amount(raw_event['tokenAmountOut'])
        else:
            raise AssertionError(f'Unexpected event type: {event_type}.')

    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    user_address = deserialize_evm_address(raw_user_address)
    pool_address = deserialize_evm_address(raw_pool_address)
    try:
        pool_address_token = EvmToken(ethaddress_to_identifier(pool_address))
    except (UnknownAsset, WrongAssetType) as e:
        raise DeserializationError(
            f'Balancer pool token with address {pool_address} should have been in the DB',
        ) from e
    token_address = deserialize_evm_address(raw_token_address)

    invest_event = BalancerInvestEvent(
        tx_hash=tx_hash,
        log_index=log_index,
        address=user_address,
        timestamp=timestamp,
        event_type=event_type,
        pool_address_token=pool_address_token,
        token_address=token_address,
        amount=amount,
    )
    return invest_event


def deserialize_pool_share(
        userdb: 'DBHandler',
        raw_pool_share: Dict[str, Any],
) -> Tuple[ChecksumEvmAddress, BalancerPoolBalance]:
    """May raise DeserializationError"""
    try:
        raw_user_address = raw_pool_share['userAddress']['id']
        user_amount = deserialize_asset_amount(raw_pool_share['balance'])
        raw_pool = raw_pool_share['poolId']
        total_amount = deserialize_asset_amount(raw_pool['totalShares'])
        raw_address = raw_pool['id']
        raw_tokens = raw_pool['tokens']
        total_weight = deserialize_asset_amount(raw_pool['totalWeight'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    if total_weight == ZERO:
        raise DeserializationError('Pool weight is zero.')

    user_address = deserialize_evm_address(raw_user_address)
    pool_address = deserialize_evm_address(raw_address)

    pool_tokens = []
    pool_token_balances = []
    for raw_token in raw_tokens:
        try:
            raw_token_address = raw_token['address']
            token_symbol = raw_token['symbol']
            token_name = raw_token['name']
            token_decimals = raw_token['decimals']
            token_total_amount = deserialize_asset_amount(raw_token['balance'])
            token_weight = deserialize_asset_amount(raw_token['denormWeight'])
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        token_address = deserialize_evm_address(raw_token_address)

        token = get_or_create_evm_token(
            userdb=userdb,
            symbol=token_symbol,
            evm_address=token_address,
            chain=ChainID.ETHEREUM,
            name=token_name,
            decimals=token_decimals,
        )
        if token_total_amount == ZERO:
            raise DeserializationError(f'Token {token.identifier} balance is zero.')

        weight = token_weight * 100 / total_weight
        token_user_amount = user_amount / total_amount * token_total_amount
        pool_token_balance = BalancerPoolTokenBalance(
            token=token,
            total_amount=token_total_amount,
            user_balance=Balance(amount=token_user_amount),
            weight=weight,
        )
        pool_token_balances.append(pool_token_balance)
        pool_token = UnderlyingToken(
            address=token.evm_address,
            token_kind=EvmTokenKind.ERC20,
            weight=weight / 100,
        )
        pool_tokens.append(pool_token)

    pool_tokens.sort(key=lambda x: x.address)
    pool_token_balances.sort(key=lambda x: x.token.evm_address)
    balancer_pool_token = get_or_create_evm_token(
        userdb=userdb,
        symbol='BPT',
        evm_address=pool_address,
        chain=ChainID.ETHEREUM,
        protocol='balancer',
        decimals=18,  # All BPT tokens have 18 decimals
        underlying_tokens=pool_tokens,
        form_with_incomplete_data=True,  # since some may not have had decimals input correctly
    )
    pool = BalancerPoolBalance(
        pool_token=balancer_pool_token,
        underlying_tokens_balance=pool_token_balances,
        total_amount=total_amount,
        user_balance=Balance(amount=user_amount),
    )
    return user_address, pool


def deserialize_transaction_id(raw_tx_id: str) -> Tuple[EVMTxHash, int]:
    """This function deserializes a Balancer's transaction id from the Graph API to
    get the transaction hash & log index.
    May raise:
    - DeserializationError if there's an error splitting the raw transaction id or
    deserializing the tx_hash.
    """
    try:
        tx_hash, raw_log_index = raw_tx_id.split('-')
        log_index = int(raw_log_index)
        deserialized_tx_hash = deserialize_evm_tx_hash(tx_hash)
    except ValueError as e:
        raise DeserializationError(f'Unexpected transaction id: {raw_tx_id}.') from e
    return deserialized_tx_hash, log_index


def deserialize_token_price(
        raw_token_price: Dict[str, Any],
) -> Tuple[ChecksumEvmAddress, Price]:
    """May raise DeserializationError"""
    try:
        token_address = raw_token_price['id']
        usd_price = deserialize_price(raw_token_price['price'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    token_address = deserialize_evm_address(token_address)

    return token_address, usd_price


def deserialize_token_day_data(
        raw_token_day_data: Dict[str, Any],
) -> Tuple[ChecksumEvmAddress, Price]:
    """May raise DeserializationError"""
    try:
        token_address = raw_token_day_data['token']['id']
        usd_price = deserialize_price(raw_token_day_data['priceUSD'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    token_address = deserialize_evm_address(token_address)

    return token_address, usd_price
