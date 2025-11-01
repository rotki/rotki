from eth_utils import to_checksum_address
import pytest

from rotkehlchen.db.lido_csm import DBLidoCsm, LidoCsmNodeOperator
from rotkehlchen.errors.misc import InputError


def test_add_and_list_node_operators(database) -> None:
    db = DBLidoCsm(database)
    address = to_checksum_address('0xBEEF00000000000000000000000000000000BEEF')
    db.add_node_operator(address=address, node_operator_id=1)

    assert db.get_node_operators() == (LidoCsmNodeOperator(address=address, node_operator_id=1),)


def test_duplicate_node_operator_id(database) -> None:
    db = DBLidoCsm(database)
    address = to_checksum_address('0x1111000000000000000000000000000000001111')
    db.add_node_operator(address=address, node_operator_id=7)

    with pytest.raises(InputError):
        db.add_node_operator(
            address=to_checksum_address('0x2222000000000000000000000000000000002222'),
            node_operator_id=7,
        )


def test_remove_node_operator(database) -> None:
    db = DBLidoCsm(database)
    address = to_checksum_address('0x1234000000000000000000000000000000005678')
    db.add_node_operator(address=address, node_operator_id=3)

    db.remove_node_operator(address=address, node_operator_id=3)
    assert db.get_node_operators() == ()

    with pytest.raises(InputError):
        db.remove_node_operator(address=address, node_operator_id=3)
