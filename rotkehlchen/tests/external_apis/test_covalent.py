from rotkehlchen.externalapis.covalent import convert_transaction_from_covalent
from rotkehlchen.types import CovalentTransaction


def test_deserialize_transaction_from_covalent():
    # Make sure that a missing to address due to contract creation is handled
    data = {
        'tx_hash': '0x2e7dcb4bde3b66954d315084fa556da75ba21c596db3d64addb6bbd04ac963cf',
        'block_signed_at': "2021-07-19T19:58:56Z",
        'block_height': 2715724,
        'from_address': "0xac9be1372ab5fc54cdf4dd2afe7a678e94706e82",
        'to_address': "0x1c0fe0a000f6df48b2dabf86a19934dd6b6f9477",
        'value': "0",
        'gas_offered': 244422,
        'gas_spent': 162948,
        'gas_price': 225000000000,
        'input_data': '0x',
        'nonce': 0,
    }
    transaction = convert_transaction_from_covalent(data)
    assert transaction == CovalentTransaction(
        tx_hash="0x2e7dcb4bde3b66954d315084fa556da75ba21c596db3d64addb6bbd04ac963cf",
        timestamp=1626739136,
        block_number=2715724,
        from_address='0xac9be1372ab5fc54cdf4dd2afe7a678e94706e82',
        to_address='0x1c0fe0a000f6df48b2dabf86a19934dd6b6f9477',
        value=0,
        gas=244422,
        gas_price=225000000000,
        gas_used=162948,
        input_data='0x',
        nonce=0,
    )
