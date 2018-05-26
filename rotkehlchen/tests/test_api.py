

def test_add_remove_blockchain_account(rotkehlchen_instance):
    """Test for issue 66 https://github.com/rotkehlchenio/rotkehlchen/issues/66"""
    rotkehlchen_instance.add_blockchain_account('ETH', '0x00d74c25bbf93df8b2a41d82b0076843b4db0349')
    rotkehlchen_instance.remove_blockchain_account('ETH', '0x00d74C25bBf93Df8B2A41d82B0076843B4dB0349')
