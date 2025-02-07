from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.interfaces.balances import (
    PROTOCOLS_WITH_BALANCES,
    ProtocolWithGauges,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent


class VelodromeLikeBalances(ProtocolWithGauges):
    """
    Query balances in Velodrome-like gauges.
    LP tokens are already queried by the normal token detection.
    """

    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer | BaseInquirer',
            tx_decoder: 'OptimismTransactionDecoder | BaseTransactionDecoder',
            counterparty: PROTOCOLS_WITH_BALANCES,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=counterparty,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED)},  # noqa: E501
            gauge_deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},  # noqa: E501
        )

    def get_gauge_address(self, event: 'EvmEvent') -> ChecksumEvmAddress | None:
        return event.address
