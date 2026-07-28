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
from rotkehlchen.history.events.structures.base import get_event_direction
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
