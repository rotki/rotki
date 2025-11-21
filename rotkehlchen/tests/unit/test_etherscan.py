from rotkehlchen.externalapis.etherscan_like import _hashes_tuple_to_list


def test_hashes_tuple_to_list():
    hashes = {('0x1', 1), ('0x2', 2), ('0x3', 3), ('0x4', 4), ('0x5', 5)}
    assert _hashes_tuple_to_list(hashes) == ['0x1', '0x2', '0x3', '0x4', '0x5']
