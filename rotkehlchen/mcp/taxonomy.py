from __future__ import annotations

from operator import itemgetter
from typing import Any, Final

from rotkehlchen.accounting.constants import (
    DEFAULT,
    EVENT_CATEGORY_DETAILS,
    EVENT_CATEGORY_MAPPINGS,
    EVENT_GROUPING_ORDER,
    EXCHANGE,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import get_event_direction
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location

# Representative exchange used to resolve the ``EXCHANGE`` reading of the few type/subtype
# combos that mean something different on a centralized exchange than they do on chain.
EXCHANGE_LOCATION: Final = Location.KRAKEN

# Rules an agent cannot infer from the data and gets wrong every time without them.
TAXONOMY_RULES: Final = (
    (
        'direction is the field to aggregate on, and it is authoritative: it is resolved by '
        'the same rotki function the rest of the app uses, not guessed from event_type. "in" '
        'means value entered the portfolio, "out" that it left, "neutral" that nothing moved.'
    ),
    (
        'Every event_type = "informational" row resolves to direction "neutral", including '
        'MEV and block-production rewards. Those rows are the relayer/beacon-chain report of '
        'a reward whose actual value arrives separately as its own event, so summing them '
        'alongside the real ones double counts the reward. Filter on direction, not on '
        'event_type, and this is handled for you.'
    ),
    (
        'Subtypes containing "wrapped" (receive wrapped / return wrapped) are protocol '
        'wrapping: the user exchanges a token for its wrapped representation. They are '
        'transfers, not income or expense, even though value moves.'
    ),
    (
        'Sum a single currency. Use the value column (main currency, present only when the '
        'session was refreshed with include_values=true) for money questions; amount_float '
        'is denominated in each row own asset, so summing it across assets is meaningless.'
    ),
)


# Worked SQLite queries over the loaded tables. Each says what it answers and what it leaves
# out, because the exclusion is usually the part an agent gets wrong.
RECIPES: Final[tuple[dict[str, Any], ...]] = (
    {
        'question': 'What did I pay in gas fees each year, in my main currency?',
        'requires': ['history_events (refreshed with include_values=true)'],
        'sql': (
            'select year, sum(value) as gas_cost, count(*) as events, '
            'sum(price_missing) as unpriced '
            "from history_events where event_subtype = 'fee' and counterparty = 'gas' "
            'group by year order by year'
        ),
        'excludes': (
            'Only counterparty "gas" fees, so exchange and protocol fees are not in this '
            'total. Check the unpriced count: those rows contribute nothing to the sum.'
        ),
    },
    {
        'question': 'What were my staking rewards worth per year?',
        'requires': ['history_events (refreshed with include_values=true)'],
        'sql': (
            'select year, sum(value) as income, count(*) as events '
            "from history_events where event_type = 'staking' and direction = 'in' "
            'group by year order by year'
        ),
        'excludes': (
            'Filtering on direction = "in" drops the informational rows, which are the '
            'relayer/beacon-chain report of a reward that also arrives as a real event. '
            'Without that filter every MEV and block-production reward is counted twice.'
        ),
    },
    {
        'question': 'What did each swap actually trade, both sides together?',
        'requires': ['history_events'],
        'sql': (
            'select spent.datetime, spent.asset as sold_asset, '
            'spent.amount_float as sold_amount, received.asset as bought_asset, '
            'received.amount_float as bought_amount '
            'from history_events spent join history_events received '
            'on received.group_identifier_hash = spent.group_identifier_hash '
            "where spent.event_subtype = 'spend' and received.event_subtype = 'receive' "
            'and received.sequence_index > spent.sequence_index '
            'order by spent.timestamp desc limit 50'
        ),
        'excludes': (
            'The fee leg is a third row in the same group and is not joined here. Join on '
            'group_identifier_hash, not group_identifier: identifiers are hashed, and the '
            'hash is stable within this session so joins and GROUP BY still work.'
        ),
    },
    {
        'question': 'Which counterparties did most of my value leave to?',
        'requires': ['history_events (refreshed with include_values=true)'],
        'sql': (
            'select counterparty, sum(value) as total_out, count(*) as events '
            "from history_events where direction = 'out' and value is not null "
            'group by counterparty order by total_out desc limit 10'
        ),
        'excludes': (
            'Rows with no cached price are skipped rather than counted as zero, so this '
            'ranks only what could be valued. Events with no counterparty group under null.'
        ),
    },
    {
        'question': 'Does my net historical flow per asset line up with my current balance?',
        'requires': ['history_events', 'balances'],
        'sql': (
            "select h.asset, sum(case when h.direction = 'in' then h.amount_float "
            "when h.direction = 'out' then -h.amount_float else 0 end) as net_amount, "
            'b.amount_float as current_balance '
            'from history_events h left join balances b on b.asset = h.asset '
            'group by h.asset order by abs(net_amount) desc limit 20'
        ),
        'excludes': (
            'Neutral-direction events contribute nothing, which is intended. A gap between '
            'net_amount and current_balance usually means the history is incomplete for '
            'that asset rather than that the balance is wrong -- check source.completeness.'
        ),
    },
)


def _describe(
        event_type: Any,
        event_subtype: Any,
        category: Any,
        location: Location | None = None,
) -> dict[str, Any]:
    """Describe one type/subtype/category combination.

    ``direction`` comes from ``get_event_direction`` rather than straight off the category,
    because that function carries overrides the raw mapping does not -- most importantly that
    an ``informational`` event is always neutral, which is what stops an agent double
    counting MEV rewards. Reading the enum directly would report those as incoming.
    """
    details = EVENT_CATEGORY_DETAILS[category][DEFAULT]
    direction = get_event_direction(
        event_type=event_type,
        event_subtype=event_subtype,
        location=location,
    )
    return {
        'category': category.serialize(),
        'label': details.label,
        'direction': direction.serialize() if direction is not None else None,
        'group': category.group.serialize(),
    }


def resolve_direction(
        event_type: Any,
        event_subtype: Any,
        location: Any = None,
) -> str | None:
    """Resolve one serialized event to rotki's own ``in``/``out``/``neutral`` direction.

    Takes the serialized strings as they appear in the analytics frame and returns None for
    anything that does not parse, so a single unrecognized event cannot fail a whole load.
    """
    try:
        parsed_type = HistoryEventType.deserialize(event_type)
        parsed_subtype = (
            HistoryEventSubType.deserialize(event_subtype)
            if isinstance(event_subtype, str) else HistoryEventSubType.NONE
        )
        parsed_location = Location.deserialize(location) if isinstance(location, str) else None
    except DeserializationError:
        return None

    direction = get_event_direction(
        event_type=parsed_type,
        event_subtype=parsed_subtype,
        location=parsed_location,
    )
    return direction.serialize() if direction is not None else None


def get_event_taxonomy() -> dict[str, Any]:
    """Derive the full event type/subtype taxonomy from rotki's own mappings.

    Everything is generated at call time, so a subtype added upstream shows up here without
    touching any MCP code.
    """
    entries: list[dict[str, Any]] = []
    for event_type, subtypes in EVENT_CATEGORY_MAPPINGS.items():
        for event_subtype, by_key in subtypes.items():
            entry = {
                'event_type': event_type.serialize(),
                'event_subtype': event_subtype.serialize(),
            } | _describe(event_type, event_subtype, by_key[DEFAULT])
            if (exchange_category := by_key.get(EXCHANGE)) is not None:
                entry['exchange'] = _describe(
                    event_type=event_type,
                    event_subtype=event_subtype,
                    category=exchange_category,
                    location=EXCHANGE_LOCATION,
                )
            entries.append(entry)

    return {
        'rules': list(TAXONOMY_RULES),
        'recipes': [dict(recipe) for recipe in RECIPES],
        'entries': entries,
        'exchange_note': (
            'An entry carrying an "exchange" block reads differently depending on where it '
            'happened: use that block for rows whose location is a centralized exchange, and '
            'the top-level reading otherwise.'
        ),
        'grouped_event_types': {
            event_type.serialize(): {
                subtype.serialize(): order
                for subtype, order in sorted(order_by_subtype.items(), key=itemgetter(1))
            }
            for event_type, order_by_subtype in EVENT_GROUPING_ORDER.items()
        },
        'grouping_note': (
            'The event types in grouped_event_types span several rows sharing one '
            'group_identifier, ordered by sequence_index as shown. One trade is a row for '
            'what was spent, a row for what was received and a row for the fee, each in its '
            'own asset -- so summing amount_float over event_type = "trade" adds unrelated '
            'currencies together. Self-join on group_identifier to recover both sides.'
        ),
    }
