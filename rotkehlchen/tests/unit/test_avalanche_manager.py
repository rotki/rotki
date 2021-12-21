def test_get_transaction_receipt(avalanche_manager):
    tx_hash = '0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d'
    result = avalanche_manager.get_transaction_receipt(
        '0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d',
    )
    assert result['hash'] == tx_hash
    assert len(result['log_events']) == 5
    assert result['gas_price'] == 225000000000
    assert result['gas_offered'] == 195000
    assert result['from_address'] == '0x4f59ae4374d93b7087f2afa6db95815b43d1c2da'
    assert result['to_address'] == "0xe54ca86531e17ef3616d22ca28b0d458b6c89106"
