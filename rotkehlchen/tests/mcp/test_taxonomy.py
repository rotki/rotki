import subprocess  # noqa: S404  -- fresh interpreter is the only way to assert import weight
import sys

from rotkehlchen.accounting.constants import DEFAULT, EVENT_CATEGORY_MAPPINGS
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.mcp.taxonomy import get_event_taxonomy


def _entry(taxonomy: dict, event_type: str, event_subtype: str) -> dict:
    return next(
        entry for entry in taxonomy['entries']
        if entry['event_type'] == event_type and entry['event_subtype'] == event_subtype
    )


def test_taxonomy_should_cover_every_mapped_combination() -> None:
    """Derived, not hand-written: adding a subtype upstream must surface it here untouched."""
    taxonomy = get_event_taxonomy()
    assert {
        (entry['event_type'], entry['event_subtype']) for entry in taxonomy['entries']
    } == {
        (event_type.serialize(), event_subtype.serialize())
        for event_type, subtypes in EVENT_CATEGORY_MAPPINGS.items()
        for event_subtype in subtypes
    }


def test_every_combination_should_have_a_direction() -> None:
    taxonomy = get_event_taxonomy()
    assert all(
        entry['direction'] in {'in', 'out', 'neutral'} for entry in taxonomy['entries']
    )
    assert all(entry['category'] and entry['label'] and entry['group']
               for entry in taxonomy['entries'])


def test_informational_events_should_be_neutral() -> None:
    """The double-count guard. rotki reports the same MEV reward twice -- once as the
    relayer's ``informational`` note and once as the real ``staking`` event -- so the
    informational row must read as moving no value. Taking direction off the category enum
    instead of rotki's resolver reports it as ``in`` and silently inflates staking income.
    """
    taxonomy = get_event_taxonomy()
    assert _entry(taxonomy, 'informational', 'mev reward')['direction'] == 'neutral'
    assert _entry(taxonomy, 'informational', 'block production')['direction'] == 'neutral'
    assert _entry(taxonomy, 'staking', 'mev reward')['direction'] == 'in'
    # every informational combination, not just the two that bite
    assert all(
        entry['direction'] == 'neutral'
        for entry in taxonomy['entries'] if entry['event_type'] == 'informational'
    )
    # ... and the raw mapping really does disagree, which is why the resolver is used
    assert EVENT_CATEGORY_MAPPINGS[HistoryEventType.INFORMATIONAL][
        HistoryEventSubType.MEV_REWARD
    ][DEFAULT].direction.serialize() == 'in'


def test_taxonomy_should_expose_swap_leg_order() -> None:
    grouped = get_event_taxonomy()['grouped_event_types']
    assert grouped['trade'] == {'spend': 0, 'receive': 1, 'fee': 2}
    assert grouped['exchange transfer'] == {'spend': 0, 'receive': 0, 'fee': 1}


def test_taxonomy_should_expose_exchange_specific_reading() -> None:
    """A deposit means something different on an exchange than on chain; both are exposed."""
    entry = _entry(get_event_taxonomy(), 'deposit', 'deposit asset')
    assert entry['exchange']['category'] == 'cex deposit'
    assert entry['exchange']['direction'] in {'in', 'out', 'neutral'}


def test_mcp_import_should_stay_free_of_flask_gevent_and_web3() -> None:
    """The MCP runs as its own lightweight process next to the app. Pulling the web stack in
    through a taxonomy import was a blocking review point on the original MCP PR.
    """
    result = subprocess.run(
        [
            sys.executable, '-c',
            (
                'import sys; import rotkehlchen.mcp.taxonomy; '
                'import rotkehlchen.mcp.tools.taxonomy; '
                "print(sorted({m.split('.')[0] for m in sys.modules} & "
                "{'flask', 'gevent', 'web3'}))"
            ),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == '[]'
