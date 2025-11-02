import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.modules.lido_csm.constants import (
    ACCOUNTING_ABI,
    CPT_LIDO_CSM,
    LIDO_CSM_ACCOUNTING_CONTRACT,
    STETH_ABI,
)
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmMetricsFetcher
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_STETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.lido_csm import DBLidoCsm
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LidoCsmBalances(ProtocolWithBalance):
    """Queries Lido CSM accounting contract for node operator bond balances."""

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_LIDO_CSM,
            deposit_event_types=set(),
        )
        self._node_operator_db = DBLidoCsm(self.event_db.db)
        self._steth_token = A_STETH.resolve_to_evm_token()
        self._accounting_contract = EvmContract(
            address=LIDO_CSM_ACCOUNTING_CONTRACT,
            abi=ACCOUNTING_ABI,
            deployed_block=0,
        )
        self._steth_contract = EvmContract(
            address=self._steth_token.evm_address,
            abi=STETH_ABI,
            deployed_block=0,
        )
        # Reuse the metrics fetcher to compute pending rewards in stETH
        self._metrics_fetcher = LidoCsmMetricsFetcher(evm_inquirer=evm_inquirer)

    def _get_bond_shares(self, node_operator_id: int) -> int:
        return self._accounting_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getBondShares',
            arguments=[node_operator_id],
        )

    def _convert_shares_to_steth(self, shares: int) -> FVal:
        return asset_normalized_value(
            amount=self._steth_contract.call(
                node_inquirer=self.evm_inquirer,
                method_name='getPooledEthByShares',
                arguments=[shares],
            ),
            asset=self._steth_token,
        )

    def query_balances(self) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        node_operators = self._node_operator_db.get_node_operators()
        if len(node_operators) == 0:
            return balances

        steth_price = Inquirer.find_usd_price(A_STETH)
        for entry in node_operators:
            # Fetch bond shares and convert to stETH
            bond_steth = ZERO
            try:
                shares = self._get_bond_shares(entry.node_operator_id)
                if shares != 0:
                    bond_steth = self._convert_shares_to_steth(shares=shares)
            except RemoteError as e:
                log.error(
                    f'Failed to fetch/convert Lido CSM bond shares for node operator '
                    f'{entry.node_operator_id} due to {e}',
                )

            # Fetch pending rewards (stETH) using the metrics fetcher
            rewards_steth = ZERO
            try:
                stats = self._metrics_fetcher.get_operator_stats(entry.node_operator_id)
                rewards_steth = stats.rewards_steth
            except RemoteError as e:
                log.error(
                    f'Failed to fetch Lido CSM pending rewards for node operator '
                    f'{entry.node_operator_id} due to {e}',
                )

            if (total_steth := bond_steth + rewards_steth) == ZERO:
                continue

            balances[entry.address].assets[self._steth_token][self.counterparty] += Balance(
                amount=total_steth,
                usd_value=total_steth * steth_price,
            )

        return balances
