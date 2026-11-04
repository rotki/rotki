import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import from_wei

from .constants import CPT_KILN, KILN_EXIT_QUEUE_ABI

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class KilnBalances(ProtocolWithBalance):
    """Query the ETH still locked in Kiln pooled staking exit tickets.

    The receipt token leaves the wallet when an exit is requested, so without this the
    value would be invisible until the ticket is claimed. The staked position itself is
    the receipt token, which is a regular token balance priced at its exchange rate.
    """

    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EVMTransactionDecoder,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_KILN,
            deposit_event_types={(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED)},
        )

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        """Query the ETH that can still be claimed with each exit ticket.

        A ticket keeps its index when it is partially claimed and re-issued, and the
        ticket() view looks tickets up by index, so the id printed at the exit request
        always returns the current state of the ticket. maxExitable is reduced by every
        claim and the ticket size drops to zero once it is fully claimed.
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        tickets: list[tuple[ChecksumEvmAddress, ChecksumEvmAddress, int]] = []
        for user_address, events in self.addresses_with_deposits(location_labels=addresses).items():  # noqa: E501
            for event in events:
                if event.extra_data is None:
                    continue

                tickets.extend(
                    (user_address, ticket['exit_queue'], int(ticket['ticket_id']))
                    for ticket in event.extra_data.get('tickets', [])
                )

        if len(tickets) == 0:
            return balances

        exit_queue_contract = EvmContract(  # only used for encoding/decoding. The call targets are the tickets' exit queues.  # noqa: E501
            address=tickets[0][1],
            abi=KILN_EXIT_QUEUE_ABI,
            deployed_block=0,
        )
        try:
            results = self.evm_inquirer.multicall(calls=[(
                exit_queue,
                exit_queue_contract.encode(method_name='ticket', arguments=[ticket_id]),
            ) for _, exit_queue, ticket_id in tickets])
        except RemoteError as e:
            log.error('Failed to query Kiln exit tickets', error=str(e))
            return balances

        amounts: list[tuple[ChecksumEvmAddress, Asset, FVal]] = []
        for (user_address, _, ticket_id), result in zip(tickets, results, strict=True):
            _, size, max_exitable = exit_queue_contract.decode(
                result=result,
                method_name='ticket',
                arguments=[ticket_id],
            )[0]
            if size == 0:
                continue  # fully claimed

            amounts.append((user_address, A_ETH, from_wei(FVal(max_exitable))))

        self._add_priced_balances(balances=balances, amounts=amounts)
        return balances
