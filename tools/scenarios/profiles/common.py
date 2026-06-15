"""Shared event-generation helpers used by the profile modules.

Profiles supply the distribution constants; this module turns them into real
event-structure objects so all serialization stays in the production classes.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from eth_utils import to_checksum_address

from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.types import (
        ChainID,
        ChecksumEvmAddress,
        EvmTransaction,
        Location,
        TimestampMS,
    )
    from tools.scenarios.deterministic import DeterministicFactory

GAS_COUNTERPARTY: Final = 'gas'

# the ERC20 Transfer event topic as a hex string, for raw receipt-log seeding
ERC20_TRANSFER_TOPIC: Final = '0x' + ERC20_OR_ERC721_TRANSFER.hex()

# Fixed USD prices per symbol, seeded as manual latest prices so that any
# balance valuation resolves locally instead of asking remote oracles.
USD_PRICES: Final = {
    'ETH': '3000', 'WETH': '3000', 'stETH': '2990', 'rETH': '3300',
    'BTC': '60000', 'WBTC': '60000',
    'USDC': '1', 'USDC.e': '1', 'USDT': '1', 'DAI': '1', 'EUR': '1.08',
    'LINK': '15', 'UNI': '9', 'AAVE': '160', 'CRV': '0.5', 'LDO': '1.8',
    'MKR': '1500', 'SNX': '2.5', 'PEPE': '0.00001', 'ARB': '0.8', 'OP': '1.9',
    'PICKLE': '1.2', 'LQTY': '1.0', 'LRC': '0.15', 'LUSD': '1',
}

CHAIN_STATE_SEED_OFFSET: Final = 0xC0FFEE  # decouple from the profile's event rng stream


def make_chain_state(
        seed: int,
        accounts: 'Sequence[ChecksumEvmAddress]',
        assets: 'Sequence[tuple[Asset, str]]',
        chain_id: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Deterministic on-chain holdings (native + ERC-20) for the accounts.

    Returns (mock_state, expected): mock_state holds raw base-unit integers
    keyed the way the mock rpc layer looks them up (chain id, lowercased
    addresses) and is written to chain_state.json; expected holds the same
    balances as human-readable amounts keyed by asset identifier, emitted
    into expected.json so correctness suites assert the exact values the
    frontend should end up displaying.

    Uses its own seeded factory (not the profile's) so adding chain state
    never shifts the rng stream behind already-modeled profile data.
    """
    from rotkehlchen.errors.asset import WrongAssetType  # avoid import cycle at module load
    from tools.scenarios.deterministic import DeterministicFactory

    factory = DeterministicFactory(seed + CHAIN_STATE_SEED_OFFSET)
    state_accounts: dict[str, Any] = {}
    expected: dict[str, Any] = {}
    for account in accounts:
        native_amount = factory.amount(0.05, 30, 6)
        holdings = {
            'native': str((native_amount * 10**18).to_int(exact=True)),
            'tokens': (tokens := {}),
        }
        expected_assets = {'ETH': str(native_amount)}
        for asset, symbol in assets:
            try:
                token = asset.resolve_to_evm_token()
            except WrongAssetType:
                continue  # the chain's native asset is handled above
            if token.decimals is None:
                continue
            price = float(USD_PRICES[symbol])
            amount = factory.amount(10 / price, 20000 / price, min(6, token.decimals))
            tokens[token.evm_address.lower()] = str(
                (amount * 10**token.decimals).to_int(exact=True),
            )
            expected_assets[token.identifier] = str(amount)
        state_accounts[account.lower()] = holdings
        expected[account] = expected_assets
    return {str(chain_id): state_accounts}, expected


def make_snapshots(
        factory: 'DeterministicFactory',
        assets: 'Sequence[tuple[Asset, str]]',
        weeks: int,
        location_weights: 'Sequence[tuple[Location, float]]',
) -> tuple[list[tuple], list[tuple], int]:
    """Weekly balance snapshots over the profile lifetime.

    Returns (timed_balances rows, timed_location_data rows, snapshot count).
    Amounts ramp up towards the present with some jitter, mirroring how real
    portfolios accumulate. Location rows include the 'total' entry that the
    netvalue statistics endpoint reads.
    """
    from rotkehlchen.fval import FVal  # avoid import cycle at module load
    from tools.scenarios.deterministic import SCENARIO_NOW

    base_amounts = {symbol: factory.amount(0.5, 200, 4) for _, symbol in assets}
    balance_rows, location_rows = [], []
    for week in range(weeks):
        timestamp = SCENARIO_NOW - (weeks - 1 - week) * 7 * 24 * 3600
        growth = FVal(f'{(week + 1) / weeks * factory.rng.uniform(0.9, 1.1):.6f}')
        total = FVal(0)
        for asset, symbol in assets:
            amount = base_amounts[symbol] * growth
            usd_value = amount * FVal(USD_PRICES[symbol])
            total += usd_value
            balance_rows.append(
                ('A', timestamp, asset.identifier, str(amount), str(usd_value)),
            )
        for location, weight in location_weights:
            location_rows.append((
                timestamp,
                location.serialize_for_db(),
                str(total * FVal(f'{weight}')),
            ))
        location_rows.append((timestamp, 'H', str(total)))  # 'H' = total; netvalue reads it
    return balance_rows, location_rows, weeks


def erc20(chain_id: int, address: str) -> str:
    """ERC-20 asset identifier with the address checksummed at build time, so
    profile constants cannot silently carry a wrongly-cased address."""
    return f'eip155:{chain_id}/erc20:{to_checksum_address(address)}'


# Tokens that the default-active modules (pickle_finance, liquity, loopring)
# may price during a balances query even with zero positions. Seeding manual
# prices keeps those lookups local instead of cascading into remote oracles.
MODULE_TOKEN_PRICES: Final = (
    (erc20(1, '0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5'), 'PICKLE'),
    (erc20(1, '0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D'), 'LQTY'),
    (erc20(1, '0xBBBBCA6A901C926f240B89eAdB51e8818B5b97eF'), 'LRC'),
    (erc20(1, '0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'), 'LUSD'),
)


# Kinds of non-gas events inside an EVM transaction group and their weights.
# 'swap' emits a spend/receive pair (two sequence slots).
EVM_EVENT_KINDS: Final = ('receive', 'spend', 'approval', 'deposit', 'withdrawal', 'swap')
EVM_EVENT_KIND_WEIGHTS: Final = (0.28, 0.22, 0.12, 0.12, 0.08, 0.18)


@dataclass(frozen=True)
class EvmPools:
    """Distribution pools for generating EVM events on one chain"""
    dex_counterparties: 'Sequence[str]'
    dex_weights: 'Sequence[float]'
    defi_counterparties: 'Sequence[str]'
    defi_weights: 'Sequence[float]'
    assets: 'Sequence[tuple[Asset, str]]'  # (asset, symbol-for-notes)
    asset_weights: 'Sequence[float]'
    gas_asset: 'Asset'


def make_evm_tx_group(
        factory: 'DeterministicFactory',
        pools: EvmPools,
        location: 'Location',
        account: 'ChecksumEvmAddress',
        timestamp: 'TimestampMS',
        size: int,
) -> list[EvmEvent]:
    """One transaction's worth of decoded events: a gas fee event plus
    ``size - 1`` further events sampled from the kind distribution."""
    tx_hash = factory.evm_tx_hash()
    gas_amount = factory.amount(0.00004, 0.015, 10)
    events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=location,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=pools.gas_asset,
        amount=gas_amount,
        location_label=account,
        counterparty=GAS_COUNTERPARTY,
        notes=f'Burn {gas_amount} ETH for gas',
    )]
    sequence_index = 1
    while sequence_index < size:
        asset, symbol = factory.weighted_choice(pools.assets, pools.asset_weights)
        amount = factory.amount(0.5, 5000, 8)
        kind = factory.weighted_choice(EVM_EVENT_KINDS, EVM_EVENT_KIND_WEIGHTS)
        if kind == 'swap' and sequence_index + 1 >= size:
            kind = 'receive'  # no room left for a pair

        if kind == 'swap':
            counterparty = factory.weighted_choice(pools.dex_counterparties, pools.dex_weights)
            receive_asset, receive_symbol = factory.weighted_choice(
                pools.assets, pools.asset_weights,
            )
            receive_amount = factory.amount(0.5, 5000, 8)
            events.extend((
                EvmEvent(
                    tx_ref=tx_hash,
                    sequence_index=sequence_index,
                    timestamp=timestamp,
                    location=location,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.SPEND,
                    asset=asset,
                    amount=amount,
                    location_label=account,
                    counterparty=counterparty,
                    notes=f'Swap {amount} {symbol} in {counterparty}',
                ),
                EvmEvent(
                    tx_ref=tx_hash,
                    sequence_index=sequence_index + 1,
                    timestamp=timestamp,
                    location=location,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.RECEIVE,
                    asset=receive_asset,
                    amount=receive_amount,
                    location_label=account,
                    counterparty=counterparty,
                    notes=f'Receive {receive_amount} {receive_symbol} as the result of a swap in {counterparty}',  # noqa: E501
                ),
            ))
            sequence_index += 2
            continue

        if kind == 'receive':
            event_type, event_subtype = HistoryEventType.RECEIVE, HistoryEventSubType.NONE
            counterparty, address = None, factory.evm_address()
            notes = f'Receive {amount} {symbol} from {address}'
        elif kind == 'spend':
            event_type, event_subtype = HistoryEventType.SPEND, HistoryEventSubType.NONE
            counterparty, address = None, factory.evm_address()
            notes = f'Send {amount} {symbol} to {address}'
        elif kind == 'approval':
            event_type, event_subtype = HistoryEventType.INFORMATIONAL, HistoryEventSubType.APPROVE
            counterparty, address = None, factory.evm_address()
            notes = f'Set {symbol} spending approval of {account} by {address} to {amount}'
        elif kind == 'deposit':
            event_type, event_subtype = HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET
            counterparty = factory.weighted_choice(pools.defi_counterparties, pools.defi_weights)
            address = factory.evm_address()
            notes = f'Deposit {amount} {symbol} into {counterparty}'
        else:  # withdrawal
            event_type, event_subtype = HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET  # noqa: E501
            counterparty = factory.weighted_choice(pools.defi_counterparties, pools.defi_weights)
            address = factory.evm_address()
            notes = f'Withdraw {amount} {symbol} from {counterparty}'

        events.append(EvmEvent(
            tx_ref=tx_hash,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=account,
            counterparty=counterparty,
            address=address,
            notes=notes,
        ))
        sequence_index += 1

    return events


def _address_topic(address: 'ChecksumEvmAddress') -> str:
    """Left-pad a 20-byte address into a 32-byte log-topic hex string."""
    return '0x' + '0' * 24 + address[2:].lower()


def make_decodable_evm_transactions(
        factory: 'DeterministicFactory',
        chain_id: 'ChainID',
        from_address: 'ChecksumEvmAddress',
        to_address: 'ChecksumEvmAddress',
        token_address: str,
        count: int,
        logs_per_tx: int = 3,
) -> tuple[list['EvmTransaction'], list[dict[str, Any]]]:
    """Build ``count`` ERC20-transfer transactions plus their receipts, decodable offline.

    The bench mock serves no receipts, so a redecode operation can only run if the
    transactions and their receipts already live in the DB. Each transaction carries a gas
    fee plus ``logs_per_tx`` Transfer logs between two tracked accounts (the most common
    shape the decoder processes) so a redecode actually emits transfer events rather than
    just gas. Returns ``(transactions, raw-receipt dicts)`` ready for
    ``ProfileBuilder.add_evm_transactions_with_receipts``.
    """
    from rotkehlchen.types import EvmTransaction, Timestamp  # local import to avoid load cycle
    from tools.scenarios.deterministic import SCENARIO_NOW

    from_topic, to_topic = _address_topic(from_address), _address_topic(to_address)
    transactions, receipts = [], []
    for idx in range(count):
        tx_hash = factory.evm_tx_hash()
        transactions.append(EvmTransaction(
            tx_hash=tx_hash,
            chain_id=chain_id,
            timestamp=Timestamp(SCENARIO_NOW - count + idx),
            block_number=18000000 + idx,
            from_address=from_address,
            to_address=token_address,  # type: ignore[arg-type]  # the token contract
            value=0,
            gas=45000,
            gas_price=10**10,
            gas_used=45000,
            input_data=b'',
            nonce=idx,
        ))
        receipts.append({
            'transactionHash': tx_hash.hex(),  # EVMTxHash.hex() already includes the 0x prefix
            'type': '0x0',
            'status': 1,
            'contractAddress': None,
            'logs': [
                {
                    'logIndex': log_idx,
                    'data': '0x' + ((idx + log_idx + 1) * 1000000).to_bytes(32, 'big').hex(),
                    'address': token_address,
                    'topics': [ERC20_TRANSFER_TOPIC, from_topic, to_topic],
                }
                for log_idx in range(logs_per_tx)
            ],
        })

    return transactions, receipts


def make_exchange_swap(
        factory: 'DeterministicFactory',
        location: 'Location',
        timestamp: 'TimestampMS',
        spend: 'tuple[Asset, str]',
        receive: 'tuple[Asset, str]',
        unique_suffix: str,
        fee_asset: 'Asset | None' = None,
) -> list[SwapEvent]:
    """An exchange trade: spend/receive pair, optionally with a fee event"""
    group_identifier = f'{location!s}-swap-{unique_suffix}'
    events = [
        SwapEvent(
            timestamp=timestamp,
            location=location,
            event_subtype=HistoryEventSubType.SPEND,
            asset=spend[0],
            amount=factory.amount(0.5, 5000, 8),
            group_identifier=group_identifier,
        ),
        SwapEvent(
            timestamp=timestamp,
            location=location,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=receive[0],
            amount=factory.amount(0.5, 5000, 8),
            group_identifier=group_identifier,
        ),
    ]
    if fee_asset is not None:
        events.append(SwapEvent(
            timestamp=timestamp,
            location=location,
            event_subtype=HistoryEventSubType.FEE,
            asset=fee_asset,
            amount=factory.amount(0.01, 25, 8),
            group_identifier=group_identifier,
        ))
    return events


def make_asset_movement(
        factory: 'DeterministicFactory',
        location: 'Location',
        timestamp: 'TimestampMS',
        asset: 'tuple[Asset, str]',
        is_deposit: bool,
        unique_suffix: str,
        with_fee: bool,
) -> list[AssetMovement]:
    """An exchange deposit or withdrawal, optionally with a fee event"""
    subtype = HistoryEventSubType.RECEIVE if is_deposit else HistoryEventSubType.SPEND
    movements = [AssetMovement(
        timestamp=timestamp,
        location=location,
        event_subtype=subtype,
        asset=asset[0],
        amount=factory.amount(1, 10000, 8),
        unique_id=unique_suffix,
    )]
    if with_fee:
        movements.append(AssetMovement(
            timestamp=timestamp,
            location=location,
            event_subtype=HistoryEventSubType.FEE,
            asset=asset[0],
            amount=factory.amount(0.01, 5, 8),
            group_identifier=movements[0].group_identifier,
        ))
    return movements


def make_staking_reward(
        factory: 'DeterministicFactory',
        location: 'Location',
        timestamp: 'TimestampMS',
        asset: 'tuple[Asset, str]',
        unique_suffix: str,
) -> 'HistoryBaseEntry':
    amount = factory.amount(0.001, 50, 8)
    return HistoryEvent(
        group_identifier=f'{location!s}-reward-{unique_suffix}',
        sequence_index=0,
        timestamp=timestamp,
        location=location,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=asset[0],
        amount=amount,
        notes=f'Receive {amount} {asset[1]} as staking reward',
    )
