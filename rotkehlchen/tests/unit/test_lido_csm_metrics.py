from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pytest

from rotkehlchen.chain.ethereum.modules.lido_csm.constants import LidoCsmOperatorType
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmMetricsFetcher
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import IPFSRemoteError, RemoteError
from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


class DummyContract:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses

    def call(self, *, method_name: str, arguments: list[int] | tuple[int, ...] = (), **_: object) -> object:  # noqa: E501
        response = self.responses[method_name]
        if isinstance(response, RemoteError):
            raise response
        if callable(response):
            return response(*arguments)
        return response


@pytest.mark.parametrize('failure', [
    None, 'distributedShares', 'getPooledEthByShares', 'ipfs',
])
def test_lido_csm_metrics_fetcher_converts_values(failure: str | None) -> None:
    """The given rewards tree is used for the rewards, None (IPFS failed) makes them
    unknown, and an on-chain failure fails the whole stats"""
    accounting_contract = DummyContract({
        'getBondCurveId': 0,
        'getBondSummaryShares': (10**18, 2 * 10**18),
        'getClaimableBondShares': 5 * 10**17,
    })
    module_contract = DummyContract({
        'getNodeOperatorSummary': (0, 0, 0, 0, 0, 0, 42, 0),
    })
    steth_contract = DummyContract({
        'getPooledEthByShares': lambda shares: shares,
    })
    fee_distributor_contract = DummyContract({
        'distributedShares': 2 * 10**17,
    })

    fetcher = LidoCsmMetricsFetcher(
        evm_inquirer=cast('EthereumInquirer', SimpleNamespace()),
    )
    fetcher.accounting_contract = accounting_contract  # type: ignore[assignment]
    fetcher.module_contract = module_contract  # type: ignore[assignment]
    fetcher.steth_contract = steth_contract  # type: ignore[assignment]
    fetcher.fee_distributor_contract = fee_distributor_contract  # type: ignore[assignment]
    if failure == 'distributedShares':
        fee_distributor_contract.responses[failure] = RemoteError(f'{failure} failed')
    elif failure == 'getPooledEthByShares':
        def fail_pending_conversion(shares: int) -> int:
            if shares == 3 * 10**17:
                raise RemoteError(f'{failure} failed')
            return shares

        steth_contract.responses[failure] = fail_pending_conversion

    rewards_tree = None if failure == 'ipfs' else {7: 5 * 10**17}
    if failure is not None and failure != 'ipfs':
        with pytest.raises(RemoteError, match=f'{failure} failed'):
            fetcher.get_operator_stats(7, rewards_tree=rewards_tree)
        return

    stats = fetcher.get_operator_stats(7, rewards_tree=rewards_tree)

    assert stats.operator_type == LidoCsmOperatorType.PERMISSIONLESS
    assert stats.current_bond == FVal('1')
    assert stats.required_bond == FVal('2')
    assert stats.claimable_bond == FVal('0.5')
    assert stats.total_deposited_validators == 42

    serialized = stats.serialize()
    assert serialized['operator_type']['label'] == 'Permissionless'
    assert serialized['bond']['current'] == '1'
    # rewards pending: cumulative(0.5e18) - distributed(0.2e18) = 0.3e18 => 0.3 stETH
    assert serialized['rewards']['pending'] == (None if failure == 'ipfs' else '0.3')
    assert serialized['keys']['total_deposited'] == 42


def test_lido_csm_rewards_tree_or_none() -> None:
    """An IPFS failure means unknown rewards (None), but the on-chain cid query failing
    is an RPC failure that is raised, so it isn't reported as an IPFS problem"""
    fetcher = _make_rewards_fetcher()
    with patch.object(
        fetcher,
        '_fetch_ipfs_json',
        return_value={'values': [{'value': [7, 5 * 10**17]}]},
    ):
        assert fetcher.get_rewards_tree_or_none() == {7: 5 * 10**17}

    with patch.object(fetcher, '_fetch_ipfs_json', side_effect=IPFSRemoteError('429')):
        assert fetcher.get_rewards_tree_or_none() is None

    fetcher.fee_distributor_contract = DummyContract({  # type: ignore[assignment]
        'treeCid': RemoteError('treeCid failed'),
    })
    with (
        patch.object(fetcher, '_fetch_ipfs_json') as fetch_ipfs,
        pytest.raises(RemoteError, match='treeCid failed'),
    ):
        fetcher.get_rewards_tree_or_none()

    assert fetch_ipfs.call_count == 0


def _make_rewards_fetcher(distributed_shares: int = 0) -> LidoCsmMetricsFetcher:
    fetcher = LidoCsmMetricsFetcher(
        evm_inquirer=cast('EthereumInquirer', SimpleNamespace()),
    )
    fetcher.steth_contract = DummyContract({  # type: ignore[assignment]
        'getPooledEthByShares': lambda shares: shares,
    })
    fetcher.fee_distributor_contract = DummyContract({  # type: ignore[assignment]
        'treeCid': 'bafkreiXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        'distributedShares': distributed_shares,
    })
    return fetcher


def test_lido_csm_rewards_tree_skips_malformed_entries() -> None:
    fetcher = _make_rewards_fetcher()
    with patch.object(fetcher, '_fetch_ipfs_json', return_value={'values': [
        {'value': [1]},  # too short
        {'value': 'not a list'},
        {'value': ['not an id', 5]},
        {'value': [2, 10**18]},
        [3, 2 * 10**18],  # an entry can be the value itself
    ]}):
        assert fetcher.get_rewards_tree() == {2: 10**18, 3: 2 * 10**18}


def test_lido_csm_pending_rewards() -> None:
    fetcher = _make_rewards_fetcher(distributed_shares=2 * 10**17)
    assert fetcher.get_pending_rewards(
        node_operator_id=7,
        rewards_tree={7: 5 * 10**17},
    ) == FVal('0.3')
    # not in the tree, or with more distributed than the tree has
    assert fetcher.get_pending_rewards(node_operator_id=8, rewards_tree={7: 5 * 10**17}) == ZERO
    assert fetcher.get_pending_rewards(node_operator_id=7, rewards_tree={7: 10**17}) == ZERO


def test_lido_csm_operator_type_matches_onchain_curve_ids() -> None:
    """Curve ids as assigned by the mainnet CSM gates and CSAccounting.DEFAULT_BOND_CURVE_ID"""
    assert LidoCsmOperatorType(0).label == 'Permissionless'
    assert LidoCsmOperatorType(1).label == 'Early Adopter'
    assert LidoCsmOperatorType(2).label == 'ICS'
    assert LidoCsmOperatorType(3).label == 'Identified DVT Cluster'
