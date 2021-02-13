from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.tests.utils.factories import make_ethereum_address


def test_loopring_accountid_mapping(database):
    db = DBLoopring(database)
    id1 = 55
    id2 = 67
    addr1 = make_ethereum_address()
    addr2 = make_ethereum_address()

    assert db.get_accountid_mapping(addr1) is None
    db.add_accountid_mapping(addr1, id1)
    assert db.get_accountid_mapping(addr1) == id1
    db.add_accountid_mapping(addr2, id2)
    assert db.get_accountid_mapping(addr2) == id2

    # assure nothing happens with non existing address
    db.remove_accountid_mapping(make_ethereum_address())

    db.remove_accountid_mapping(addr1)
    assert db.get_accountid_mapping(addr1) is None
