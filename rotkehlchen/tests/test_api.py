import pytest


def test_add_remove_blockchain_account(rotkehlchen_instance):
    """Test for issue 66 https://github.com/rotkehlchenio/rotkehlchen/issues/66"""
    rotkehlchen_instance.add_blockchain_account(
        'ETH',
        '0x00d74c25bbf93df8b2a41d82b0076843b4db0349'
    )
    rotkehlchen_instance.remove_blockchain_account(
        'ETH',
        '0x00d74C25bBf93Df8B2A41d82B0076843B4dB0349'
    )


@pytest.mark.parametrize('number_of_accounts', [0])
def test_add_remove_eth_tokens(rotkehlchen_instance):
    """Test for issue 83 https://github.com/rotkehlchenio/rotkehlchen/issues/83"""
    # Addition of tokens into the DB fires up balance checks for each account
    # we got. For that reason we give 0 accounts for this test

    tokens_to_add = ['STORJ', 'GNO', 'RDN']
    rotkehlchen_instance.add_owned_eth_tokens(tokens_to_add)
    db_tokens_list = rotkehlchen_instance.data.db.get_owned_tokens()
    assert set(tokens_to_add) == set(db_tokens_list)

    rotkehlchen_instance.remove_owned_eth_tokens(['STORJ', 'GNO'])
    db_tokens_list = rotkehlchen_instance.data.db.get_owned_tokens()
    assert len(db_tokens_list) == 1 and db_tokens_list[0] == 'RDN'
