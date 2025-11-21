from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from rotkehlchen.chain.ethereum.modules.lido_csm.constants import LidoCsmOperatorType
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmMetricsFetcher
from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


class DummyContract:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses

    def call(self, *, method_name: str, arguments: list[int] | tuple[int, ...] = (), **_: object) -> object:  # noqa: E501
        response = self.responses[method_name]
        if callable(response):
            return response(*arguments)
        return response


def test_lido_csm_metrics_fetcher_converts_values() -> None:
    accounting_contract = DummyContract({
        'getBondCurveId': 1,
        'getBondSummaryShares': (10**18, 2 * 10**18),
        'getClaimableBondShares': 5 * 10**17,
    })
    module_contract = DummyContract({
        'getNodeOperatorTotalDepositedKeys': 42,
    })
    steth_contract = DummyContract({
        'getPooledEthByShares': lambda shares: shares,
    })
    fee_distributor_contract = DummyContract({
        'treeCid': 'bafkreiXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        'distributedShares': 2 * 10**17,
    })

    fetcher = LidoCsmMetricsFetcher(
        evm_inquirer=cast('EthereumInquirer', SimpleNamespace()),
    )
    fetcher.accounting_contract = accounting_contract  # type: ignore[assignment]
    fetcher.module_contract = module_contract  # type: ignore[assignment]
    fetcher.steth_contract = steth_contract  # type: ignore[assignment]
    fetcher.fee_distributor_contract = fee_distributor_contract  # type: ignore[assignment]

    def fake_fetch_ipfs_json(cid: str) -> dict[str, Any]:
        return {
            'values': [
                {'value': [7, 5 * 10**17]},  # for node operator id 7
            ],
        }

    fetcher._fetch_ipfs_json = fake_fetch_ipfs_json  # type: ignore[method-assign]

    stats = fetcher.get_operator_stats(7)

    assert stats.operator_type == LidoCsmOperatorType.PERMISSIONLESS
    assert stats.current_bond == FVal('1')
    assert stats.required_bond == FVal('2')
    assert stats.claimable_bond == FVal('0.5')
    assert stats.total_deposited_validators == 42

    serialized = stats.serialize()
    assert serialized['operator_type']['label'] == 'Permissionless'
    assert serialized['bond']['current'] == '1'
    # rewards pending: cumulative(0.5e18) - distributed(0.2e18) = 0.3e18 => 0.3 stETH
    assert serialized['rewards']['pending'] == '0.3'
    assert serialized['keys']['total_deposited'] == 42
