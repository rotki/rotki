"""Current Frankencoin savings positions.

This is deliberately only a scaffold. Unlike the decoder, which explains past
transactions, this module will query current contract state for open positions.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.frankencoin.constants import CPT_FRANKENCOIN
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

from .constants import SAVINGS_CONTRACT_ABI, SAVINGS_CONTRACT_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress


class FrankencoinSavingsBalances(ProtocolWithBalance):
    """Query deposited savings and expose them as balances of the underlying asset."""

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            tx_decoder: EVMTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_FRANKENCOIN,  # type: ignore[arg-type]  # TODO: add to PROTOCOLS_WITH_BALANCES when registering this class  # noqa: E501
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
            },
        )
        self.savings_contract = SAVINGS_CONTRACT_ADDRESS[evm_inquirer.chain_id]

    def query_balances(self) -> BalancesSheetType:
        """Return current savings positions for addresses with decoded deposits.

        TODO: Use addresses_with_deposits() to discover relevant users, query
        their current position from self.savings, convert internal units to
        redeemable ZCHF, and add priced ZCHF balances via _add_priced_balances().
        """

        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := self.addresses_with_deposits()) == 0:
            return balances

        addresses_with_savings_chf = set()
        for address, events in addresses_with_deposits.items():
            for event in events:
                if event.event_type == HistoryEventType.DEPOSIT_TO_PROTOCOL:
                    None
                    # TODO

        savings_contract = EvmContract(
            address=self.savings_contract,
            abi=SAVINGS_CONTRACT_ABI,
            deployed_block=0,  # is not used here
        )
        return defaultdict(BalanceSheet)

    def _query_savings_zchf_balances(
                self,
                balances: BalancesSheetType,
                addresses: list[ChecksumEvmAddress],
        ) -> BalancesSheetType:
        return defaultdict(BalanceSheet)
