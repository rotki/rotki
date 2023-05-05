from typing import TYPE_CHECKING

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import BCH_BSV_FORK_TS, BTC_BCH_FORK_TS, ETH_DAO_FORK_TS
from rotkehlchen.constants.assets import A_BCH, A_BSV, A_BTC, A_ETC, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Price, Timestamp

if TYPE_CHECKING:
    from .base import CostBasisCalculator


def handle_prefork_asset_acquisitions(
        cost_basis: 'CostBasisCalculator',
        location: Location,
        timestamp: Timestamp,
        asset: Asset,
        amount: FVal,
        price: Price,
        ignored_asset_ids: set[str],
        starting_index: int,
) -> list['ProcessedAccountingEvent']:
    """
        Calculate the prefork asset acquisitions, meaning how is the acquisition
        of ETC pre ETH fork handled etc.

        TODO: This should change for https://github.com/rotki/rotki/issues/1610

        Returns the acquisition events to append to the pot
    """
    acquisitions = []
    if asset == A_ETH and timestamp < ETH_DAO_FORK_TS:
        acquisitions = [(A_ETC, 'Prefork acquisition for ETC')]
    elif asset == A_BTC and timestamp < BTC_BCH_FORK_TS:
        # Acquiring BTC before the BCH fork provides equal amount of BCH and BSV
        acquisitions = [
            (A_BCH, 'Prefork acquisition for BCH'),
            (A_BSV, 'Prefork acquisition for BSV'),
        ]
    elif asset == A_BCH and timestamp < BCH_BSV_FORK_TS:
        # Acquiring BCH before the BSV fork provides equal amount of BSV
        acquisitions = [(A_BSV, 'Prefork acquisition for BSV')]

    events = []
    for acquisition in acquisitions:
        if acquisition[0].identifier in ignored_asset_ids:
            continue
        event = ProcessedAccountingEvent(
            type=AccountingEventType.PREFORK_ACQUISITION,
            notes=acquisition[1],
            location=location,
            timestamp=timestamp,
            asset=acquisition[0],
            taxable_amount=amount,
            free_amount=ZERO,
            price=price,
            pnl=PNL(),
            cost_basis=None,
            index=starting_index,
        )
        cost_basis.obtain_asset(event)
        events.append(event)
        starting_index += 1

    return events


def handle_prefork_asset_spends(
        cost_basis: 'CostBasisCalculator',
        asset: Asset,
        amount: FVal,
        timestamp: Timestamp,
) -> None:
    """
    Calculate the prefork asset spends, meaning the opposite of
    handle_prefork_asset_acquisitions

    TODO: This should change for https://github.com/rotki/rotki/issues/1610
    """
    # For now for those don't use inform_user_missing_acquisition since if those hit
    # the preforked asset acquisition data is what's missing so user would getLogger
    # two messages. So as an example one for missing ETH data and one for ETC data
    if asset == A_ETH and timestamp < ETH_DAO_FORK_TS:
        cost_basis.reduce_asset_amount(asset=A_ETC, amount=amount, timestamp=timestamp)

    if asset == A_BTC and timestamp < BTC_BCH_FORK_TS:
        cost_basis.reduce_asset_amount(asset=A_BCH, amount=amount, timestamp=timestamp)
        cost_basis.reduce_asset_amount(asset=A_BSV, amount=amount, timestamp=timestamp)

    if asset == A_BCH and timestamp < BCH_BSV_FORK_TS:
        cost_basis.reduce_asset_amount(asset=A_BSV, amount=amount, timestamp=timestamp)
