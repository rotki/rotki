import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.api.websockets.typedefs import UserMessageRecord
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.modules.lido_csm.constants import (
    CPT_LIDO_CSM,
    LIDO_STETH_DEPLOYED_BLOCK,
    STETH_ABI,
    LidoCsmStakingModule,
)
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmMetricsFetcher
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_STETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.lido_csm import DBLidoCsm
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import IPFSRemoteError, RemoteError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import NetworkFailure

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LidoCsmBalances(ProtocolWithBalance):
    """Queries Lido CSM accounting contract for node operator bond balances."""

    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EthereumTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_LIDO_CSM,
            deposit_event_types=set(),
        )
        self._node_operator_db = DBLidoCsm(self.event_db.db)
        self._steth_contract = EvmContract(
            address=A_STETH.resolve_to_evm_token().evm_address,
            abi=STETH_ABI,
            deployed_block=LIDO_STETH_DEPLOYED_BLOCK,
        )
        # Reuse the metrics fetchers to compute pending rewards in stETH
        self._metrics_fetchers = {
            staking_module: LidoCsmMetricsFetcher(
                evm_inquirer=evm_inquirer,
                staking_module=staking_module,
            ) for staking_module in LidoCsmStakingModule
        }

    def _get_bond_shares(
            self,
            node_operator_id: int,
            staking_module: LidoCsmStakingModule,
    ) -> int:
        """Fetch the raw bond shares for a node operator.

        May raise:
            RemoteError: if the contract call fails.
        """
        return self._metrics_fetchers[staking_module].accounting_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getBondShares',
            arguments=[node_operator_id],
        )

    def _convert_shares_to_steth(self, shares: int) -> FVal:
        """Convert stETH shares to normalized stETH balances.

        May raise:
            RemoteError: if the contract call fails.
        """
        pooled_eth = self._steth_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getPooledEthByShares',
            arguments=[shares],
        )
        return token_normalized_value_decimals(pooled_eth, 18)

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        """Return the Lido CSM balances tracked in the DB for stETH."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(node_operators := self._node_operator_db.get_node_operators(
            addresses=addresses,
        )) == 0:
            return balances

        if (steth_price := Inquirer.find_price(
                from_asset=A_STETH,
                to_asset=CachedSettings().main_currency,
        )) == ZERO:
            log.error('Failed to fetch stETH price; reporting values as zero.')

        rewards_trees: dict[LidoCsmStakingModule, dict[int, int] | None] = {}
        rewards_failed, ipfs_failed, last_error = False, False, ''

        for entry in node_operators:
            # Fetch bond shares and convert to stETH
            bond_steth = ZERO
            try:
                if (shares := self._get_bond_shares(
                    node_operator_id=entry.node_operator_id,
                    staking_module=entry.staking_module,
                )) != 0:
                    bond_steth = self._convert_shares_to_steth(shares=shares)
            except RemoteError as e:
                log.error(
                    f'Failed to fetch/convert Lido CSM bond shares for node operator '
                    f'{entry.node_operator_id} ({entry.staking_module.name}) due to {e}',
                )
                continue

            # Fetch pending rewards (stETH) from the staking module's rewards tree, fetched once
            # and shared by its operators. If they can't be fetched fall back to the last stored
            # value, if any, instead of reporting them as zero.
            metrics_fetcher = self._metrics_fetchers[entry.staking_module]
            if entry.staking_module not in rewards_trees:
                rewards_trees[entry.staking_module] = None
                try:
                    rewards_trees[entry.staking_module] = metrics_fetcher.get_rewards_tree()
                except RemoteError as e:
                    ipfs_failed |= isinstance(e, IPFSRemoteError)
                    last_error = str(e)
                    log.error(
                        'Failed to fetch the Lido CSM rewards tree of %s due to %s',
                        entry.staking_module.name,
                        e,
                    )

            rewards_steth: FVal | None = None
            if (rewards_tree := rewards_trees[entry.staking_module]) is not None:
                try:
                    rewards_steth = metrics_fetcher.get_pending_rewards(
                        node_operator_id=entry.node_operator_id,
                        rewards_tree=rewards_tree,
                    )
                except RemoteError as e:
                    last_error = str(e)
                    log.error(
                        'Failed to fetch Lido CSM pending rewards for node operator %s (%s) '
                        'due to %s',
                        entry.node_operator_id,
                        entry.staking_module.name,
                        e,
                    )

            if rewards_steth is None:
                rewards_failed = True
                rewards_steth = entry.metrics.rewards_steth if entry.metrics is not None else None

            if (total_steth := bond_steth + (rewards_steth or ZERO)) == ZERO:
                continue

            balances[entry.address].assets[A_STETH][self.counterparty] += Balance(
                amount=total_steth,
                value=total_steth * steth_price,
            )

        if rewards_failed:
            message = (
                'Could not fetch the Lido CSM rewards from any IPFS gateway. '
                if ipfs_failed else
                'Could not fetch the Lido CSM rewards due to an on-chain query failure. '
            )
            message += (
                'The pending rewards shown are the last known values, '
                'or missing if there are none.'
            )
            if ipfs_failed:
                message += ' You can set your own IPFS gateway in the settings.'
            self.evm_inquirer.database.msg_aggregator.add_warning(
                message,
                classification=NetworkFailure(record=UserMessageRecord.BALANCE, error=last_error),
                subject=LOCATION_ETHEREUM,
            )

        return balances
