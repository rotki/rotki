import pytest
from eth_utils import to_checksum_address

from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmNodeOperatorStats
from rotkehlchen.db.lido_csm import DBLidoCsm, LidoCsmNodeOperator
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address


def test_lido_csm_db_operations(database) -> None:
    db = DBLidoCsm(database)

    # Happy path add/list
    address = make_evm_address()
    db.add_node_operator(address=address, node_operator_id=1)
    assert db.get_node_operators() == (
        LidoCsmNodeOperator(address=address, node_operator_id=1, metrics=None),
    )

    # Duplicate add should fail
    with pytest.raises(InputError):
        db.add_node_operator(
            address=address,
            node_operator_id=1,
        )

    # Metrics lifecycle
    stats = LidoCsmNodeOperatorStats(
        operator_type_id=1,
        operator_type_label='Permissionless',
        current_bond=FVal('1.0'),
        required_bond=FVal('2.0'),
        claimable_bond=FVal('0.5'),
        total_deposited_keys=42,
        rewards_steth=FVal('0.3'),
    )
    db.set_metrics(node_operator_id=1, metrics=stats)
    assert db.get_node_operators() == (
        LidoCsmNodeOperator(
            address=address,
            node_operator_id=1,
            metrics=stats,
        ),
    )
    db.delete_metrics(node_operator_id=1)
    assert db.get_node_operators() == (
        LidoCsmNodeOperator(address=address, node_operator_id=1, metrics=None),
    )

    # Remove happy path and double remove error
    db.remove_node_operator(address=address, node_operator_id=1)
    assert db.get_node_operators() == ()
    with pytest.raises(InputError):
        db.remove_node_operator(address=address, node_operator_id=1)

    # Wrong-address removal error
    tracked_address = to_checksum_address('0xBEEF00000000000000000000000000000000BEEF')
    wrong_address = to_checksum_address('0xDEAD00000000000000000000000000000000BEEF')
    db.add_node_operator(address=tracked_address, node_operator_id=9)
    with pytest.raises(InputError):
        db.remove_node_operator(address=wrong_address, node_operator_id=9)
