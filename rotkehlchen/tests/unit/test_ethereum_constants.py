from eth_utils import is_checksum_address


def test_ethereum_contracts(ethereum_contracts):
    """Test that all ethereum contract entries have legal data"""
    for _, entry in ethereum_contracts.contracts.items():
        assert len(entry) == 3
        assert is_checksum_address(entry['address'])
        assert entry['deployed_block'] > 0
        assert isinstance(entry['abi'], list)


def test_ethereum_abi(ethereum_contracts):
    """Test that the ethereum abi entries have legal data"""
    for _, entry in ethereum_contracts.abi_entries.items():
        assert isinstance(entry, list)
