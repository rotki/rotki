from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_STETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.lido_csm import DBLidoCsm, LidoCsmNodeOperator
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

from .constants import ACCOUNTING_ABI, LIDO_CSM_ACCOUNTING_CONTRACT, STETH_ABI, CPT_LIDO_CSM
from .metrics import LidoCsmMetricsFetcher

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
            node_operator_db: DBLidoCsm | None = None,
            accounting_contract: EvmContract | None = None,
            steth_contract: EvmContract | None = None,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_LIDO_CSM,
            deposit_event_types=set(),
        )
        self._node_operator_db = node_operator_db or DBLidoCsm(self.event_db.db)
        self._steth_token = A_STETH.resolve_to_evm_token()
        self._accounting_contract = accounting_contract or EvmContract(
            address=LIDO_CSM_ACCOUNTING_CONTRACT,
            abi=ACCOUNTING_ABI,
            deployed_block=0,
        )
        self._steth_contract = steth_contract or EvmContract(
            address=self._steth_token.evm_address,
            abi=STETH_ABI,
            deployed_block=0,
        )
        # Reuse the metrics fetcher to compute pending rewards in stETH
        self._metrics_fetcher = LidoCsmMetricsFetcher(evm_inquirer=evm_inquirer)

    def _get_node_operators(self) -> tuple[LidoCsmNodeOperator, ...]:
        return self._node_operator_db.get_node_operators()

    def _get_bond_shares(self, node_operator_id: int) -> int:
        return self._accounting_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getBondShares',
            arguments=[node_operator_id],
        )

    def _convert_shares_to_steth(self, shares: int) -> FVal:
        pooled_eth = self._steth_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getPooledEthByShares',
            arguments=[shares],
        )
        return asset_normalized_value(pooled_eth, A_STETH)

    def query_balances(self) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        node_operators = self._get_node_operators()
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
            except RemoteError as exc:
                log.error(
                    'Failed to fetch/convert Lido CSM bond shares for node operator %s due to %s',
                    entry.node_operator_id,
                    exc,
                )

            # Fetch pending rewards (stETH) using the metrics fetcher
            rewards_steth = ZERO
            try:
                stats = self._metrics_fetcher.get_operator_stats(entry.node_operator_id)
                rewards_steth = stats.rewards_steth
            except RemoteError as exc:
                log.error(
                    'Failed to fetch Lido CSM pending rewards for node operator %s due to %s',
                    entry.node_operator_id,
                    exc,
                )

            total_steth = bond_steth + rewards_steth
            if total_steth == ZERO:
                continue

            balances[entry.address].assets[self._steth_token][self.counterparty] += Balance(
                amount=total_steth,
                usd_value=total_steth * steth_price,
            )

        return balances
