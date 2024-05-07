import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, Price

from .types import BalancerPoolBalance, BalancerPoolTokenBalance

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def deserialize_pool_share(
        userdb: 'DBHandler',
        raw_pool_share: dict[str, Any],
) -> tuple[ChecksumEvmAddress, BalancerPoolBalance]:
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
        raise DeserializationError(f'Missing key: {e!s}.') from e

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
            raise DeserializationError(f'Missing key: {e!s}.') from e

        token_address = deserialize_evm_address(raw_token_address)

        token = get_or_create_evm_token(
            userdb=userdb,
            symbol=token_symbol,
            evm_address=token_address,
            chain_id=ChainID.ETHEREUM,
            name=token_name,
            decimals=token_decimals,
            encounter=TokenEncounterInfo(description='Querying balancer pools'),
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
        name='Balancer Pool Token',
        symbol='BPT',
        evm_address=pool_address,
        chain_id=ChainID.ETHEREUM,
        protocol='balancer',
        decimals=18,  # All BPT tokens have 18 decimals
        underlying_tokens=pool_tokens,
        encounter=TokenEncounterInfo(description='Querying balancer pools'),
    )
    pool = BalancerPoolBalance(
        pool_token=balancer_pool_token,
        underlying_tokens_balance=pool_token_balances,
        total_amount=total_amount,
        user_balance=Balance(amount=user_amount),
    )
    return user_address, pool


def deserialize_token_price(
        raw_token_price: dict[str, Any],
) -> tuple[ChecksumEvmAddress, Price]:
    """May raise DeserializationError"""
    try:
        token_address = raw_token_price['id']
        usd_price = deserialize_price(raw_token_price['price'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {e!s}.') from e

    token_address = deserialize_evm_address(token_address)

    return token_address, usd_price
