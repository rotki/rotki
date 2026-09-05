"""Notes that rotki regenerates from an event's own fields instead of storing them.

Every template here is used twice. `AutoNotesTemplate.format` builds the text in Python for
`HistoryBaseEntry.auto_notes` and `AutoNotesTemplate.to_sql` rebuilds the same text inside
SQLite, so the notes substring filter keeps matching events whose notes column is NULL.
Sharing one template string per note kind is what keeps the two from drifting apart.

The SQL side has no access to asset symbols (they live in the global DB) and substitutes the
asset identifier, which equals the symbol for the native assets that dominate these events.
"""
from string import Formatter
from typing import Final

from rotkehlchen.constants.location_details import get_formatted_location_name
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import CHAINS_WITH_TRANSACTIONS, Location


def sql_string_literal(value: str) -> str:
    """Quote a python string as an SQL string literal"""
    return "'" + value.replace("'", "''") + "'"


class AutoNotesTemplate:
    """A note template with python `str.format` placeholders that can also be rendered as an
    SQL concatenation of arbitrary column expressions, one per placeholder."""

    def __init__(self, template: str) -> None:
        self.template = template

    def format(self, **kwargs: object) -> str:
        return self.template.format(**kwargs)

    def to_sql(self, **fields: str) -> str:
        """Render the template as an SQL expression, replacing each placeholder with the given
        SQL expression for it. Placeholders missing from `fields` raise KeyError."""
        parts = []
        for literal, name, _, _ in Formatter().parse(self.template):
            if literal:
                parts.append(sql_string_literal(literal))
            if name is not None:
                parts.append(fields[name])

        return ' || '.join(parts)


# -- EVM/Solana transaction basics
GAS_TEMPLATE: Final = AutoNotesTemplate('Burn {amount} {symbol} for gas')
FAILED_GAS_TEMPLATE: Final = AutoNotesTemplate('Burn {amount} {symbol} for gas of a failed transaction')  # noqa: E501
SOLANA_FEE_TEMPLATE: Final = AutoNotesTemplate('Spend {amount} {symbol} as transaction fee')
APPROVE_TEMPLATE: Final = AutoNotesTemplate('Set {symbol} spending approval of {owner} by {spender} to {amount}')  # noqa: E501
REVOKE_APPROVAL_TEMPLATE: Final = AutoNotesTemplate('Revoke {symbol} spending approval of {owner} by {spender}')  # noqa: E501
DEPLOY_TEMPLATE: Final = AutoNotesTemplate('Deploy a new contract at {address}')
NO_VALUE_SELF_TX_TEMPLATE: Final = AutoNotesTemplate('No value transaction to self')
SELF_TX_TEMPLATE: Final = AutoNotesTemplate('Transaction to self of {amount} {symbol}')
# Native asset transfers only name the other side. Token transfers name both sides.
NATIVE_TRANSFER_TEMPLATE: Final = AutoNotesTemplate('{verb} {amount} {symbol} {preposition} {counterparty_or_address}')  # noqa: E501
TOKEN_TRANSFER_OUT_TEMPLATE: Final = AutoNotesTemplate('{verb} {amount} {symbol} from {location_label} to {counterparty_or_address}')  # noqa: E501
TOKEN_TRANSFER_IN_TEMPLATE: Final = AutoNotesTemplate('{verb} {amount} {symbol} from {counterparty_or_address} to {location_label}')  # noqa: E501
SOLANA_TRANSFER_TEMPLATE: Final = AutoNotesTemplate('{verb} {amount} {symbol}{suffix}')
# -- ETH staking
ETH_WITHDRAWAL_TEMPLATE: Final = AutoNotesTemplate('Withdraw {amount} ETH from validator {validator_index}')  # noqa: E501
ETH_EXIT_TEMPLATE: Final = AutoNotesTemplate('Exit validator {validator_index} with {amount} ETH')
ETH_BLOCK_TEMPLATE: Final = AutoNotesTemplate('Validator {validator_index} produced block {block_number} with {amount} ETH going to {fee_recipient} as the block reward')  # noqa: E501
ETH_MEV_TEMPLATE: Final = AutoNotesTemplate('Validator {validator_index} produced block {block_number}. Relayer reported {amount} ETH as the MEV reward going to {fee_recipient}')  # noqa: E501
ETH_DEPOSIT_TEMPLATE: Final = AutoNotesTemplate('Deposit {amount} ETH to validator {validator_index}')  # noqa: E501
ETH_DEPOSIT_UNKNOWN_VALIDATOR_TEMPLATE: Final = AutoNotesTemplate('Deposit {amount} ETH to validator with a not yet known validator index')  # noqa: E501
# -- Exchanges
KRAKEN_STAKING_REWARD_TEMPLATE: Final = AutoNotesTemplate('Gain {amount} {symbol} from Kraken staking')  # noqa: E501
KRAKEN_STAKING_FEE_TEMPLATE: Final = AutoNotesTemplate('Spend {amount} {symbol} as Kraken staking fee')  # noqa: E501
SWAP_SPEND_TEMPLATE: Final = AutoNotesTemplate('Swap {amount} {symbol} in {location}')
SWAP_RECEIVE_TEMPLATE: Final = AutoNotesTemplate('Receive {amount} {symbol} after a swap in {location}')  # noqa: E501
SWAP_FEE_TEMPLATE: Final = AutoNotesTemplate('Spend {amount} {symbol} as {location} swap fee')
MOVEMENT_FEE_TEMPLATE: Final = AutoNotesTemplate('Pay {amount} {symbol} as {location} {event_type} fee')  # noqa: E501
MOVEMENT_DEPOSIT_TEMPLATE: Final = AutoNotesTemplate('Deposit {amount} {symbol} to {location}')
MOVEMENT_WITHDRAWAL_TEMPLATE: Final = AutoNotesTemplate('Withdraw {amount} {symbol} from {location}')  # noqa: E501

# Verb of a plain transfer per event type, as decided by decode_transfer_direction()
TRANSFER_VERBS: Final = {
    HistoryEventType.SPEND: 'Send',
    HistoryEventType.RECEIVE: 'Receive',
    HistoryEventType.TRANSFER: 'Transfer',
    HistoryEventType.DEPOSIT: 'Deposit',
    HistoryEventType.WITHDRAWAL: 'Withdraw',
}
# Transfer types where the tracked address is the sender, so the other side is named with "to"
OUTGOING_TRANSFER_TYPES: Final = (
    HistoryEventType.SPEND,
    HistoryEventType.TRANSFER,
    HistoryEventType.DEPOSIT,
)
# Subtype a plain transfer of each type has, as decided by decode_transfer_direction()
PLAIN_TRANSFER_SUBTYPES: Final = {
    HistoryEventType.SPEND: HistoryEventSubType.NONE,
    HistoryEventType.RECEIVE: HistoryEventSubType.NONE,
    HistoryEventType.TRANSFER: HistoryEventSubType.NONE,
    HistoryEventType.DEPOSIT: HistoryEventSubType.DEPOSIT_ASSET,
    HistoryEventType.WITHDRAWAL: HistoryEventSubType.REMOVE_ASSET,
}
# Transfer types decoded only when the other side is a known exchange, which is then the counterparty  # noqa: E501
EXCHANGE_TRANSFER_TYPES: Final = (HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL)
EXCHANGE_COUNTERPARTIES: Final = frozenset(str(location) for location in ALL_SUPPORTED_EXCHANGES)
# Native asset identifier of every chain that produces onchain events, keyed by location
NATIVE_ASSET_BY_LOCATION: Final[dict[Location, str]] = {
    Location.from_chain(chain): chain.get_native_token_id()
    for chain in CHAINS_WITH_TRANSACTIONS
}


def is_plain_transfer(
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        counterparty: str | None,
) -> bool:
    """Whether the type combination is the one of an undecorated transfer, whose notes only
    name the involved addresses. Exchange deposits and withdrawals carry the exchange as
    counterparty while every other transfer has none."""
    if PLAIN_TRANSFER_SUBTYPES.get(event_type) != event_subtype:
        return False
    if event_type in EXCHANGE_TRANSFER_TYPES:
        return counterparty in EXCHANGE_COUNTERPARTIES
    return counterparty is None


# -- SQL reconstruction. Column expressions valid wherever a history events filter is applied,
# which always exposes the history_events columns and the history_events_identifier alias.
_COUNTERPARTY_SQL: Final = '(SELECT counterparty FROM chain_events_info WHERE identifier=history_events_identifier)'  # noqa: E501
_ADDRESS_SQL: Final = '(SELECT address FROM chain_events_info WHERE identifier=history_events_identifier)'  # noqa: E501
_COUNTERPARTY_OR_ADDRESS_SQL: Final = f'COALESCE({_COUNTERPARTY_SQL}, {_ADDRESS_SQL})'
_VALIDATOR_INDEX_SQL: Final = '(SELECT validator_index FROM eth_staking_events_info WHERE identifier=history_events_identifier)'  # noqa: E501
_IS_EXIT_OR_BLOCK_SQL: Final = '(SELECT is_exit_or_blocknumber FROM eth_staking_events_info WHERE identifier=history_events_identifier)'  # noqa: E501
_LOCATION_NAME_SQL: Final = 'CASE location ' + ' '.join(
    f'WHEN {sql_string_literal(location.serialize_for_db())} THEN {sql_string_literal(get_formatted_location_name(location))}'  # noqa: E501
    for location in Location
) + ' END'
_TRANSFER_VERB_SQL: Final = 'CASE type ' + ' '.join(
    f'WHEN {sql_string_literal(event_type.serialize())} THEN {sql_string_literal(verb)}'
    for event_type, verb in TRANSFER_VERBS.items()
) + ' END'
_OUTGOING_TRANSFER_SQL: Final = 'type IN (' + ', '.join(
    sql_string_literal(x.serialize()) for x in OUTGOING_TRANSFER_TYPES
) + ')'
_TRANSFER_PREPOSITION_SQL: Final = f"CASE WHEN {_OUTGOING_TRANSFER_SQL} THEN 'to' ELSE 'from' END"
_EXCHANGE_COUNTERPARTIES_SQL: Final = f'{_COUNTERPARTY_SQL} IN (' + ', '.join(
    sql_string_literal(x) for x in sorted(EXCHANGE_COUNTERPARTIES)
) + ')'
_PLAIN_TRANSFER_SQL: Final = '(' + ' OR '.join(
    f'(type={sql_string_literal(event_type.serialize())} AND subtype={sql_string_literal(subtype.serialize())} AND '  # noqa: E501
    f'{_EXCHANGE_COUNTERPARTIES_SQL if event_type in EXCHANGE_TRANSFER_TYPES else f"{_COUNTERPARTY_SQL} IS NULL"})'  # noqa: E501
    for event_type, subtype in PLAIN_TRANSFER_SUBTYPES.items()
) + ')'
_NATIVE_ASSET_SQL: Final = '(' + ' OR '.join(
    f'(location={sql_string_literal(location.serialize_for_db())} AND asset={sql_string_literal(asset_id)})'  # noqa: E501
    for location, asset_id in NATIVE_ASSET_BY_LOCATION.items()
) + ')'
_COMMON_FIELDS: Final = {'amount': 'amount', 'symbol': 'asset', 'location': _LOCATION_NAME_SQL}


def _when(condition: str, result: str) -> str:
    return f'WHEN {condition} THEN {result}'


def _kraken_staking_sql() -> str:
    common = f"location={sql_string_literal(Location.KRAKEN.serialize_for_db())} AND type='{HistoryEventType.STAKING.serialize()}'"  # noqa: E501
    return 'CASE ' + ' '.join((
        _when(f"{common} AND subtype='{HistoryEventSubType.REWARD.serialize()}'", KRAKEN_STAKING_REWARD_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
        _when(f"{common} AND subtype='{HistoryEventSubType.FEE.serialize()}'", KRAKEN_STAKING_FEE_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
    )) + ' END'


def _evm_sql() -> str:
    transfer_fields = _COMMON_FIELDS | {
        'verb': _TRANSFER_VERB_SQL,
        'preposition': _TRANSFER_PREPOSITION_SQL,
        'counterparty_or_address': _COUNTERPARTY_OR_ADDRESS_SQL,
        'location_label': 'location_label',
    }
    approval_fields = _COMMON_FIELDS | {'owner': 'location_label', 'spender': _ADDRESS_SQL}
    gas_common = f"subtype='{HistoryEventSubType.FEE.serialize()}' AND {_COUNTERPARTY_SQL}='gas'"
    approval_common = f"type='{HistoryEventType.INFORMATIONAL.serialize()}' AND subtype='{HistoryEventSubType.APPROVE.serialize()}' AND {_COUNTERPARTY_SQL} IS NULL"  # noqa: E501
    self_tx_common = f"type='{HistoryEventType.TRANSACTION_TO_SELF.serialize()}' AND subtype='{HistoryEventSubType.NONE.serialize()}'"  # noqa: E501
    return 'CASE ' + ' '.join((
        _when(f"type='{HistoryEventType.SPEND.serialize()}' AND {gas_common}", GAS_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
        _when(f"type='{HistoryEventType.FAIL.serialize()}' AND {gas_common}", FAILED_GAS_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
        _when(f"{approval_common} AND amount='0'", REVOKE_APPROVAL_TEMPLATE.to_sql(**approval_fields)),  # noqa: E501
        _when(approval_common, APPROVE_TEMPLATE.to_sql(**approval_fields)),
        _when(f"type='{HistoryEventType.DEPLOY.serialize()}'", DEPLOY_TEMPLATE.to_sql(address=_ADDRESS_SQL)),  # noqa: E501
        _when(f"{self_tx_common} AND amount='0'", NO_VALUE_SELF_TX_TEMPLATE.to_sql()),
        _when(self_tx_common, SELF_TX_TEMPLATE.to_sql(**_COMMON_FIELDS)),
        _when(f'{_PLAIN_TRANSFER_SQL} AND {_NATIVE_ASSET_SQL}', NATIVE_TRANSFER_TEMPLATE.to_sql(**transfer_fields)),  # noqa: E501
        _when(f"{_PLAIN_TRANSFER_SQL} AND asset NOT LIKE '%/erc721:%' AND {_OUTGOING_TRANSFER_SQL}", TOKEN_TRANSFER_OUT_TEMPLATE.to_sql(**transfer_fields)),  # noqa: E501
        _when(f"{_PLAIN_TRANSFER_SQL} AND asset NOT LIKE '%/erc721:%'", TOKEN_TRANSFER_IN_TEMPLATE.to_sql(**transfer_fields)),  # noqa: E501
    )) + ' END'


def _solana_sql() -> str:
    transfer_fields = _COMMON_FIELDS | {
        'verb': _TRANSFER_VERB_SQL,
        'suffix': f"CASE WHEN {_COUNTERPARTY_OR_ADDRESS_SQL} IS NULL THEN '' ELSE ' ' || {_TRANSFER_PREPOSITION_SQL} || ' ' || {_COUNTERPARTY_OR_ADDRESS_SQL} END",  # noqa: E501
    }
    return 'CASE ' + ' '.join((
        _when(f"type='{HistoryEventType.SPEND.serialize()}' AND subtype='{HistoryEventSubType.FEE.serialize()}' AND {_COUNTERPARTY_SQL}='gas'", SOLANA_FEE_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
        _when(_PLAIN_TRANSFER_SQL, SOLANA_TRANSFER_TEMPLATE.to_sql(**transfer_fields)),
    )) + ' END'


def _swap_sql() -> str:
    common = f"type='{HistoryEventType.TRADE.serialize()}'"
    return 'CASE ' + ' '.join((
        _when(f"{common} AND subtype='{HistoryEventSubType.SPEND.serialize()}'", SWAP_SPEND_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
        _when(f"{common} AND subtype='{HistoryEventSubType.RECEIVE.serialize()}'", SWAP_RECEIVE_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
        _when(f"{common} AND subtype='{HistoryEventSubType.FEE.serialize()}'", SWAP_FEE_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
    )) + ' END'


def _asset_movement_sql() -> str:
    common = f"type='{HistoryEventType.EXCHANGE_TRANSFER.serialize()}'"
    return 'CASE ' + ' '.join((
        _when(f"{common} AND subtype='{HistoryEventSubType.FEE.serialize()}'", MOVEMENT_FEE_TEMPLATE.to_sql(event_type='type', **_COMMON_FIELDS)),  # noqa: E501
        _when(f"{common} AND subtype='{HistoryEventSubType.RECEIVE.serialize()}'", MOVEMENT_DEPOSIT_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
        _when(f"{common} AND subtype='{HistoryEventSubType.SPEND.serialize()}'", MOVEMENT_WITHDRAWAL_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
    )) + ' END'


_STAKING_FIELDS: Final = {
    'amount': 'amount',
    'validator_index': _VALIDATOR_INDEX_SQL,
    'block_number': _IS_EXIT_OR_BLOCK_SQL,
    'fee_recipient': 'location_label',
}


def _eth_withdrawal_sql() -> str:
    return f'CASE WHEN {_IS_EXIT_OR_BLOCK_SQL}=1 THEN {ETH_EXIT_TEMPLATE.to_sql(**_STAKING_FIELDS)} ELSE {ETH_WITHDRAWAL_TEMPLATE.to_sql(**_STAKING_FIELDS)} END'  # noqa: E501


def _eth_block_sql() -> str:
    return f"CASE WHEN subtype='{HistoryEventSubType.MEV_REWARD.serialize()}' THEN {ETH_MEV_TEMPLATE.to_sql(**_STAKING_FIELDS)} ELSE {ETH_BLOCK_TEMPLATE.to_sql(**_STAKING_FIELDS)} END"  # noqa: E501


def _eth_deposit_sql() -> str:
    return f'CASE WHEN {_VALIDATOR_INDEX_SQL}=-1 THEN {ETH_DEPOSIT_UNKNOWN_VALIDATOR_TEMPLATE.to_sql(**_STAKING_FIELDS)} ELSE {ETH_DEPOSIT_TEMPLATE.to_sql(**_STAKING_FIELDS)} END'  # noqa: E501


# The notes rotki would generate for a history_events row whose notes column is NULL, as an
# SQL expression. Branches are keyed on entry_type first so the per-row cost is a couple of
# integer comparisons for the kinds that have no auto notes. Entry type values are those of
# HistoryBaseEntryType, spelled out since importing it here would be circular.
AUTO_NOTES_SQL: Final = 'CASE entry_type ' + ' '.join((
    _when('1', _kraken_staking_sql()),
    _when('2', _evm_sql()),
    _when('3', _eth_withdrawal_sql()),
    _when('4', _eth_block_sql()),
    _when('5', _eth_deposit_sql()),
    _when('6', _asset_movement_sql()),
    _when('7', _swap_sql()),
    _when('8', _swap_sql()),
    _when('9', _solana_sql()),
    _when('10', _swap_sql()),
)) + ' END'
