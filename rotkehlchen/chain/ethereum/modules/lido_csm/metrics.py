from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_STETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.network import query_file

from .constants import (
    ACCOUNTING_ABI,
    BOND_CURVE_TYPE_LABELS,
    CSM_MODULE_ABI,
    FEE_DISTRIBUTOR_ABI,
    LIDO_CSM_FEE_DISTRIBUTOR_CONTRACT,
    LIDO_CSM_ACCOUNTING_CONTRACT,
    LIDO_CSM_MODULE_CONTRACT,
    LIDO_CSM_IPFS_GATEWAY,
    STETH_ABI,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass
class LidoCsmNodeOperatorStats:
    operator_type_id: int
    operator_type_label: str
    current_bond: FVal
    required_bond: FVal
    claimable_bond: FVal
    total_deposited_keys: int
    rewards_steth: FVal

    def serialize(self) -> dict[str, Any]:
        return {
            'operator_type': {
                'id': self.operator_type_id,
                'label': self.operator_type_label,
            },
            'bond': {
                'current': str(self.current_bond),
                'required': str(self.required_bond),
                'claimable': str(self.claimable_bond),
            },
            'keys': {
                'total_deposited': self.total_deposited_keys,
            },
            'rewards': {
                'pending': str(self.rewards_steth),
            },
        }


class LidoCsmMetricsFetcher:
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            accounting_contract: EvmContract | None = None,
            module_contract: EvmContract | None = None,
            steth_contract: EvmContract | None = None,
            fee_distributor_contract: EvmContract | None = None,
    ) -> None:
        self.accounting_contract = accounting_contract or EvmContract(
            address=LIDO_CSM_ACCOUNTING_CONTRACT,
            abi=ACCOUNTING_ABI,
            deployed_block=0,
        )
        self.module_contract = module_contract or EvmContract(
            address=LIDO_CSM_MODULE_CONTRACT,
            abi=CSM_MODULE_ABI,
            deployed_block=0,
        )
        steth_token = A_STETH.resolve_to_evm_token()
        self.steth_contract = steth_contract or EvmContract(
            address=steth_token.evm_address,
            abi=STETH_ABI,
            deployed_block=0,
        )
        self.fee_distributor_contract = fee_distributor_contract or EvmContract(
            address=LIDO_CSM_FEE_DISTRIBUTOR_CONTRACT,
            abi=FEE_DISTRIBUTOR_ABI,
            deployed_block=0,
        )
        self.evm_inquirer = evm_inquirer

    def _convert_shares_to_steth(self, shares: int) -> FVal:
        pooled_eth = self.steth_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getPooledEthByShares',
            arguments=[shares],
        )
        return asset_normalized_value(pooled_eth, A_STETH)

    def _fetch_ipfs_json(self, cid: str) -> dict[str, Any]:
        url = f"{LIDO_CSM_IPFS_GATEWAY}{cid}"
        data = query_file(url, is_json=True)
        assert isinstance(data, dict)
        return data

    def get_operator_stats(self, node_operator_id: int) -> LidoCsmNodeOperatorStats:
        curve_id = self.accounting_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getBondCurveId',
            arguments=[node_operator_id],
        )
        operator_label = BOND_CURVE_TYPE_LABELS.get(curve_id, 'Unknown')

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

        total_deposited_keys = self.module_contract.call(
            node_inquirer=self.evm_inquirer,
            method_name='getNodeOperatorTotalDepositedKeys',
            arguments=[node_operator_id],
        )

        # Compute operator rewards pending (stETH) from fee distributor
        try:
            tree_cid = self.fee_distributor_contract.call(
                node_inquirer=self.evm_inquirer,
                method_name='treeCid',
                arguments=[],
            )
            doc = self._fetch_ipfs_json(tree_cid)
            # IPFS doc contains 'values', each with 'value': [nodeOperatorId, cumulativeShares]
            values = doc.get('values', []) if isinstance(doc, dict) else []
            cumulative_shares = 0
            for item in values:
                # Support both {'value': [id, shares]} and just [id, shares]
                val = item.get('value') if isinstance(item, dict) else item
                if (
                    isinstance(val, (list, tuple)) and
                    len(val) >= 2 and
                    int(val[0]) == int(node_operator_id)
                ):
                    # values may be string or int
                    cumulative_shares = int(val[1])
                    break
            distributed = self.fee_distributor_contract.call(
                node_inquirer=self.evm_inquirer,
                method_name='distributedShares',
                arguments=[node_operator_id],
            )
            pending_shares = max(int(cumulative_shares) - int(distributed), 0)
            rewards_steth = self._convert_shares_to_steth(pending_shares)
        except RemoteError as e:
            log.error('Failed to compute Lido CSM rewards for %s: %s', node_operator_id, e)
            rewards_steth = FVal(0)

        return LidoCsmNodeOperatorStats(
            operator_type_id=int(curve_id),
            operator_type_label=operator_label,
            current_bond=self._convert_shares_to_steth(current_shares_raw),
            required_bond=self._convert_shares_to_steth(required_shares_raw),
            claimable_bond=self._convert_shares_to_steth(claimable_raw),
            total_deposited_keys=int(total_deposited_keys),
            rewards_steth=rewards_steth,
        )
