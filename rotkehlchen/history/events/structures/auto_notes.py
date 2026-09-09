"""Notes that rotki regenerates from an event's own fields instead of storing them.

Every template here is used twice. `AutoNotesTemplate.format` builds the text in Python for
`HistoryBaseEntry.auto_notes` and `AutoNotesTemplate.to_sql` rebuilds the same text inside
SQLite, so the notes substring filter keeps matching events whose notes column is NULL.
Sharing one template string per note kind is what keeps the two from drifting apart.

The SQL side has no access to asset symbols (they live in the global DB), so it renders the
text without the symbol: the notes filter matches the words around it and searching by asset
is what the asset filter is for.
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

    def to_sql(self, **fields: str | None) -> str:
        """Render the template as an SQL expression, replacing each placeholder with the given
        SQL expression for it. A placeholder mapped to None is left out of the text together
        with the space before it. Placeholders missing from `fields` raise KeyError."""
        parts = []
        for literal, name, _, _ in Formatter().parse(self.template):
            expression = fields[name] if name is not None else None
            omitted = name is not None and expression is None
            if (text := literal.removesuffix(' ') if omitted else literal):
                parts.append(sql_string_literal(text))
            if expression is not None:
                parts.append(expression)

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
# The expression is evaluated for every candidate row of a notes search, so it is shaped to do
# as little work as possible per row: every branch is a CASE on a single column that stops at
# the first match, and the columns of the chain and staking info tables are read through one
# scalar subquery per entry type kind instead of one per placeholder.
_LOCATION_NAME_SQL: Final = 'CASE location ' + ' '.join(
    f'WHEN {sql_string_literal(location.serialize_for_db())} THEN {sql_string_literal(get_formatted_location_name(location))}'  # noqa: E501
    for location in Location
) + ' END'
_EXCHANGE_COUNTERPARTIES_SQL: Final = 'counterparty IN (' + ', '.join(
    sql_string_literal(x) for x in sorted(EXCHANGE_COUNTERPARTIES)
) + ')'
_NATIVE_ASSET_SQL: Final = 'CASE location ' + ' '.join(
    f'WHEN {sql_string_literal(location.serialize_for_db())} THEN asset={sql_string_literal(asset_id)}'  # noqa: E501
    for location, asset_id in NATIVE_ASSET_BY_LOCATION.items()
) + ' END'
_COMMON_FIELDS: Final[dict[str, str | None]] = {'amount': 'amount', 'symbol': None, 'location': _LOCATION_NAME_SQL}  # noqa: E501
_TRADE_TYPES_SQL: Final = 'type IN (' + ', '.join(
    sql_string_literal(x.serialize()) for x in (HistoryEventType.TRADE, HistoryEventType.MULTI_TRADE)  # noqa: E501
) + ')'


def _case(column: str, cases: dict[str | int, str]) -> str:
    """CASE on a column with a branch per value, NULL when none matches"""
    return f'CASE {column} ' + ' '.join(
        f'WHEN {sql_string_literal(value) if isinstance(value, str) else value} THEN {result}'
        for value, result in cases.items()
    ) + ' END'


def _if(condition: str, result: str) -> str:
    """The result when the condition holds, NULL otherwise"""
    return f'CASE WHEN {condition} THEN {result} END'


def _info_lookup(table: str, expression: str) -> str:
    """Evaluate the expression with the columns of the event's row in an info table in scope"""
    return f'(SELECT {expression} FROM {table} WHERE identifier=history_events_identifier)'


def _plain_transfer_sql(event_type: HistoryEventType, text: str) -> str:
    """The text for a row of the given type and its plain transfer subtype when the
    counterparty makes it a plain transfer, per is_plain_transfer. Valid in a
    chain_events_info lookup."""
    counterparty_check = _EXCHANGE_COUNTERPARTIES_SQL if event_type in EXCHANGE_TRANSFER_TYPES else 'counterparty IS NULL'  # noqa: E501
    return _if(counterparty_check, text)


def _transfer_type_sql(event_type: HistoryEventType, text: str) -> str:
    """Branch of a CASE on type for a type whose only generated text is the plain transfer"""
    return _case('subtype', {PLAIN_TRANSFER_SUBTYPES[event_type].serialize(): text})


def _kraken_staking_sql() -> str:
    return _if(
        f'location={sql_string_literal(Location.KRAKEN.serialize_for_db())} AND type={sql_string_literal(HistoryEventType.STAKING.serialize())}',  # noqa: E501
        _case('subtype', {
            HistoryEventSubType.REWARD.serialize(): KRAKEN_STAKING_REWARD_TEMPLATE.to_sql(**_COMMON_FIELDS),  # noqa: E501
            HistoryEventSubType.FEE.serialize(): KRAKEN_STAKING_FEE_TEMPLATE.to_sql(**_COMMON_FIELDS),  # noqa: E501
        }),
    )


def _evm_transfer_sql(event_type: HistoryEventType) -> str:
    """Plain transfer text of the given type. Native assets name only the other side, tokens
    both and ERC721 transfers have no generated text. Valid in a chain_events_info lookup."""
    outgoing = event_type in OUTGOING_TRANSFER_TYPES
    fields = _COMMON_FIELDS | {
        'verb': sql_string_literal(TRANSFER_VERBS[event_type]),
        'counterparty_or_address': 'COALESCE(counterparty, address)',
        'location_label': 'location_label',
    }
    token_template = TOKEN_TRANSFER_OUT_TEMPLATE if outgoing else TOKEN_TRANSFER_IN_TEMPLATE
    return _plain_transfer_sql(event_type, (
        f'CASE WHEN {_NATIVE_ASSET_SQL} THEN {NATIVE_TRANSFER_TEMPLATE.to_sql(preposition=sql_string_literal("to" if outgoing else "from"), **fields)} '  # noqa: E501
        f"WHEN asset NOT LIKE '%/erc721:%' THEN {token_template.to_sql(**fields)} END"
    ))


def _evm_sql() -> str:
    approval_fields = _COMMON_FIELDS | {'owner': 'location_label', 'spender': 'address'}
    gas = "counterparty='gas'"
    fee, none = HistoryEventSubType.FEE.serialize(), HistoryEventSubType.NONE.serialize()
    return _info_lookup('chain_events_info', _case('type', {
        HistoryEventType.SPEND.serialize(): _case('subtype', {
            fee: _if(gas, GAS_TEMPLATE.to_sql(**_COMMON_FIELDS)),
            none: _evm_transfer_sql(HistoryEventType.SPEND),
        }),
        HistoryEventType.RECEIVE.serialize(): _transfer_type_sql(HistoryEventType.RECEIVE, _evm_transfer_sql(HistoryEventType.RECEIVE)),  # noqa: E501
        HistoryEventType.TRANSFER.serialize(): _transfer_type_sql(HistoryEventType.TRANSFER, _evm_transfer_sql(HistoryEventType.TRANSFER)),  # noqa: E501
        HistoryEventType.DEPOSIT.serialize(): _transfer_type_sql(HistoryEventType.DEPOSIT, _evm_transfer_sql(HistoryEventType.DEPOSIT)),  # noqa: E501
        HistoryEventType.WITHDRAWAL.serialize(): _transfer_type_sql(HistoryEventType.WITHDRAWAL, _evm_transfer_sql(HistoryEventType.WITHDRAWAL)),  # noqa: E501
        HistoryEventType.FAIL.serialize(): _case('subtype', {
            fee: _if(gas, FAILED_GAS_TEMPLATE.to_sql(**_COMMON_FIELDS)),
        }),
        HistoryEventType.INFORMATIONAL.serialize(): _case('subtype', {
            HistoryEventSubType.APPROVE.serialize(): _if('counterparty IS NULL', (
                f"CASE WHEN amount='0' THEN {REVOKE_APPROVAL_TEMPLATE.to_sql(**approval_fields)} "
                f'ELSE {APPROVE_TEMPLATE.to_sql(**approval_fields)} END'
            )),
        }),
        HistoryEventType.DEPLOY.serialize(): DEPLOY_TEMPLATE.to_sql(address='address'),
        HistoryEventType.TRANSACTION_TO_SELF.serialize(): _case('subtype', {
            none: (
                f"CASE WHEN amount='0' THEN {NO_VALUE_SELF_TX_TEMPLATE.to_sql()} "
                f'ELSE {SELF_TX_TEMPLATE.to_sql(**_COMMON_FIELDS)} END'
            ),
        }),
    }))


def _solana_transfer_sql(event_type: HistoryEventType) -> str:
    """Plain transfer text of the given type, naming the other side when there is one. Valid
    in a chain_events_info lookup."""
    preposition = sql_string_literal(' to ' if event_type in OUTGOING_TRANSFER_TYPES else ' from ')
    return _plain_transfer_sql(event_type, SOLANA_TRANSFER_TEMPLATE.to_sql(
        verb=sql_string_literal(TRANSFER_VERBS[event_type]),
        suffix=f"COALESCE({preposition} || COALESCE(counterparty, address), '')",
        **_COMMON_FIELDS,
    ))


def _solana_sql() -> str:
    return _info_lookup('chain_events_info', _case('type', {
        HistoryEventType.SPEND.serialize(): _case('subtype', {
            HistoryEventSubType.FEE.serialize(): _if("counterparty='gas'", SOLANA_FEE_TEMPLATE.to_sql(**_COMMON_FIELDS)),  # noqa: E501
            HistoryEventSubType.NONE.serialize(): _solana_transfer_sql(HistoryEventType.SPEND),
        }),
        HistoryEventType.RECEIVE.serialize(): _transfer_type_sql(HistoryEventType.RECEIVE, _solana_transfer_sql(HistoryEventType.RECEIVE)),  # noqa: E501
        HistoryEventType.TRANSFER.serialize(): _transfer_type_sql(HistoryEventType.TRANSFER, _solana_transfer_sql(HistoryEventType.TRANSFER)),  # noqa: E501
        HistoryEventType.DEPOSIT.serialize(): _transfer_type_sql(HistoryEventType.DEPOSIT, _solana_transfer_sql(HistoryEventType.DEPOSIT)),  # noqa: E501
        HistoryEventType.WITHDRAWAL.serialize(): _transfer_type_sql(HistoryEventType.WITHDRAWAL, _solana_transfer_sql(HistoryEventType.WITHDRAWAL)),  # noqa: E501
    }))


def _swap_sql() -> str:
    return _if(_TRADE_TYPES_SQL, _case('subtype', {
        HistoryEventSubType.SPEND.serialize(): SWAP_SPEND_TEMPLATE.to_sql(**_COMMON_FIELDS),
        HistoryEventSubType.RECEIVE.serialize(): SWAP_RECEIVE_TEMPLATE.to_sql(**_COMMON_FIELDS),
        HistoryEventSubType.FEE.serialize(): SWAP_FEE_TEMPLATE.to_sql(**_COMMON_FIELDS),
    }))


def _asset_movement_sql() -> str:
    return _if(f'type={sql_string_literal(HistoryEventType.EXCHANGE_TRANSFER.serialize())}', _case('subtype', {  # noqa: E501
        HistoryEventSubType.FEE.serialize(): MOVEMENT_FEE_TEMPLATE.to_sql(event_type='type', **_COMMON_FIELDS),  # noqa: E501
        HistoryEventSubType.RECEIVE.serialize(): MOVEMENT_DEPOSIT_TEMPLATE.to_sql(**_COMMON_FIELDS),  # noqa: E501
        HistoryEventSubType.SPEND.serialize(): MOVEMENT_WITHDRAWAL_TEMPLATE.to_sql(**_COMMON_FIELDS),  # noqa: E501
    }))


_STAKING_FIELDS: Final = {
    'amount': 'amount',
    'validator_index': 'validator_index',
    'block_number': 'is_exit_or_blocknumber',
    'fee_recipient': 'location_label',
}


def _eth_withdrawal_sql() -> str:
    return _info_lookup('eth_staking_events_info', f'CASE WHEN is_exit_or_blocknumber=1 THEN {ETH_EXIT_TEMPLATE.to_sql(**_STAKING_FIELDS)} ELSE {ETH_WITHDRAWAL_TEMPLATE.to_sql(**_STAKING_FIELDS)} END')  # noqa: E501


def _eth_block_sql() -> str:
    return _info_lookup('eth_staking_events_info', f"CASE WHEN subtype='{HistoryEventSubType.MEV_REWARD.serialize()}' THEN {ETH_MEV_TEMPLATE.to_sql(**_STAKING_FIELDS)} ELSE {ETH_BLOCK_TEMPLATE.to_sql(**_STAKING_FIELDS)} END")  # noqa: E501


def _eth_deposit_sql() -> str:
    return _info_lookup('eth_staking_events_info', f'CASE WHEN validator_index=-1 THEN {ETH_DEPOSIT_UNKNOWN_VALIDATOR_TEMPLATE.to_sql(**_STAKING_FIELDS)} ELSE {ETH_DEPOSIT_TEMPLATE.to_sql(**_STAKING_FIELDS)} END')  # noqa: E501


# The notes rotki would generate for a history_events row whose notes column is NULL, as an
# SQL expression. Branches are keyed on entry_type first so the per-row cost is a couple of
# integer comparisons for the kinds that have no auto notes. Entry type values are those of
# HistoryBaseEntryType, spelled out since importing it here would be circular.
AUTO_NOTES_SQL: Final = _case('entry_type', {
    1: _kraken_staking_sql(),
    2: _evm_sql(),
    3: _eth_withdrawal_sql(),
    4: _eth_block_sql(),
    5: _eth_deposit_sql(),
    6: _asset_movement_sql(),
    7: _swap_sql(),
    8: _swap_sql(),
    9: _solana_sql(),
    10: _swap_sql(),
})
