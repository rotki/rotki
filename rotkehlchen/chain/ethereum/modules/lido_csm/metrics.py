import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.modules.lido_csm.constants import (
    ACCOUNTING_ABI,
    CSM_MODULE_ABI,
    FEE_DISTRIBUTOR_ABI,
    LIDO_CSM_MODULE_CONTRACTS,
    LIDO_STETH_DEPLOYED_BLOCK,
    STETH_ABI,
    LidoCsmOperatorType,
    LidoCsmStakingModule,
)
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_STETH
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import IPFSRemoteError
from rotkehlchen.externalapis.ipfs import IPFSGateway
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.fval import FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass
class LidoCsmNodeOperatorStats:
    operator_type: LidoCsmOperatorType
    current_bond: FVal
    required_bond: FVal
    claimable_bond: FVal
    total_deposited_validators: int
    rewards_steth: FVal | None  # None when the rewards could not be fetched

    def serialize(self) -> dict[str, Any]:
        operator_type_id = int(self.operator_type)
        operator_type_label = self.operator_type.label
        return {
            'operator_type': {
                'id': operator_type_id,
                'label': operator_type_label,
            },
            'bond': {
                'current': str(self.current_bond),
                'required': str(self.required_bond),
                'claimable': str(self.claimable_bond),
            },
            'keys': {
                'total_deposited': self.total_deposited_validators,
            },
            'rewards': {
                'pending': None if self.rewards_steth is None else str(self.rewards_steth),
            },
        }


class LidoCsmMetricsFetcher:
    """Fetches and normalizes Lido CSM metrics from on-chain contracts and IPFS."""
    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            staking_module: LidoCsmStakingModule,
    ) -> None:
        # TODO: share conversion logic here mirrors balances.py; extract a shared helper.
        self.staking_module = staking_module
        contracts = LIDO_CSM_MODULE_CONTRACTS[staking_module]
        self.accounting_contract = EvmContract(
            address=contracts.accounting,
            abi=ACCOUNTING_ABI,
            deployed_block=contracts.deployed_block,
        )
        self.module_contract = EvmContract(
            address=contracts.module,
            abi=CSM_MODULE_ABI,
            deployed_block=contracts.deployed_block,
        )
        self.steth_contract = EvmContract(
            address=A_STETH.resolve_to_evm_token().evm_address,
            abi=STETH_ABI,
            deployed_block=LIDO_STETH_DEPLOYED_BLOCK,
        )
        self.fee_distributor_contract = EvmContract(
            address=contracts.fee_distributor,
            abi=FEE_DISTRIBUTOR_ABI,
            deployed_block=contracts.deployed_block,
        )
        self.evm_inquirer = evm_inquirer

    def _convert_shares_to_steth(self, shares: int) -> FVal:
        """Convert stETH shares to normalized stETH amounts.

        May raise:
            RemoteError: if the stETH contract call fails.
            ValueError: if the contract returns non-numeric data.
        """
        pooled_eth = self.steth_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getPooledEthByShares',
            arguments=[shares],
        )
        return token_normalized_value_decimals(pooled_eth, 18)

    def _fetch_ipfs_json(self, cid: str) -> dict[str, Any]:
        """Fetch the fee distributor merkle tree document from IPFS.

        May raise:
            IPFSRemoteError: if the document cannot be retrieved.
        """
        return IPFSGateway(
            custom_gateway=CachedSettings().get_settings().ipfs_gateway,
        ).query_json(cid)

    def get_rewards_tree(self) -> dict[int, int]:
        """Download the fee distributor's rewards tree and return the cumulative reward
        shares of every node operator in it, by node operator id.

        May raise:
            RemoteError: if the tree's cid can't be read.
            IPFSRemoteError: if the document can't be retrieved.
        """
        tree_cid = self.fee_distributor_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='treeCid',
            arguments=[],
        )
        # An empty cid means the module has not distributed any rewards yet
        if not tree_cid:
            return {}

        doc = self._fetch_ipfs_json(tree_cid)
        # IPFS doc contains 'values', each with 'value': [nodeOperatorId, cumulativeShares]
        values = doc.get('values', []) if isinstance(doc, dict) else []
        rewards_tree: dict[int, int] = {}
        for item in values:
            val = item.get('value') if isinstance(item, dict) else item
            if not (isinstance(val, (list, tuple)) and len(val) >= 2):
                log.error('Skipping malformed Lido CSM rewards tree entry: %s', val)
                continue

            try:
                rewards_tree[int(val[0])] = int(val[1])
            except (TypeError, ValueError) as e:
                log.error('Skipping Lido CSM rewards entry %s due to parsing error: %s', val, e)

        return rewards_tree

    def get_rewards_tree_or_none(self) -> dict[int, int] | None:
        """Like get_rewards_tree, but returns None if the document can't be retrieved from
        IPFS, so that callers report the rewards as unknown instead of failing.

        May raise:
            RemoteError: if the tree's cid can't be read.
        """
        try:
            return self.get_rewards_tree()
        except IPFSRemoteError as e:
            log.error('Failed to fetch the Lido CSM rewards tree: %s', e)
            return None

    def get_pending_rewards(self, node_operator_id: int, rewards_tree: dict[int, int]) -> FVal:
        """Compute the pending rewards of a node operator, in stETH, from the result of
        get_rewards_tree. The tree has every operator's entry, so it can be reused for many.

        May raise:
            RemoteError: if a contract call fails.
        """
        distributed = self.fee_distributor_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='distributedShares',
            arguments=[node_operator_id],
        )
        pending_shares = max(rewards_tree.get(node_operator_id, 0) - int(distributed), 0)
        return self._convert_shares_to_steth(pending_shares)

    def get_operator_stats(
            self,
            node_operator_id: int,
            rewards_tree: dict[int, int] | None,
    ) -> LidoCsmNodeOperatorStats:
        """Gather and normalize bond/reward stats for a node operator.

        The rewards tree is the result of get_rewards_tree_or_none, fetched once by the
        caller and shared by every operator. None means it could not be retrieved from
        IPFS, and then the rewards are reported as None (unknown) instead of zero.

        May raise:
            RemoteError: if any contract call fails.
            ValueError: if numeric conversions from contract responses fail.
        """
        curve_id = self.accounting_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getBondCurveId',
            arguments=[node_operator_id],
        )
        operator_type = LidoCsmOperatorType.from_curve_id(
            staking_module=self.staking_module,
            curve_id=int(curve_id),
        )

        current_shares_raw, required_shares_raw = self.accounting_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getBondSummaryShares',
            arguments=[node_operator_id],
        )

        claimable_raw = self.accounting_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getClaimableBondShares',
            arguments=[node_operator_id],
        )

        *_, total_deposited_validators, _ = self.module_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getNodeOperatorSummary',
            arguments=[node_operator_id],
        )

        rewards_steth: FVal | None = None  # None: rewards could not be fetched, not zero
        if rewards_tree is not None:
            rewards_steth = self.get_pending_rewards(
                node_operator_id=node_operator_id,
                rewards_tree=rewards_tree,
            )

        return LidoCsmNodeOperatorStats(
            operator_type=operator_type,
            current_bond=self._convert_shares_to_steth(current_shares_raw),
            required_bond=self._convert_shares_to_steth(required_shares_raw),
            claimable_bond=self._convert_shares_to_steth(claimable_raw),
            total_deposited_validators=int(total_deposited_validators),
            rewards_steth=rewards_steth,
        )
