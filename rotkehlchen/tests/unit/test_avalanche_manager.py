from unittest.mock import patch

from flaky import flaky

from rotkehlchen.types import deserialize_evm_tx_hash


@flaky(max_runs=3, min_passes=1)  # covalent api might be really flaky
def test_get_transaction_receipt(avalanche_manager):
    covalent_patch = patch.object(
        avalanche_manager.covalent,
        'get_transaction_receipt',
        side_effect=lambda *args: None,  # None means no data from covalent,
    )

    tx_hash = deserialize_evm_tx_hash('0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d')  # noqa: E501
    covalent_result = avalanche_manager.get_transaction_receipt(tx_hash=tx_hash)
    with covalent_patch:
        web3_result = avalanche_manager.get_transaction_receipt(tx_hash=tx_hash)

    assert covalent_result['hash'] == web3_result['hash'] == tx_hash
    assert covalent_result['blockNumber'] == web3_result['blockNumber'] == 2716404
    assert covalent_result['from'] == web3_result['from'] == '0x4F59aE4374D93b7087F2aFa6Db95815b43d1C2dA'  # noqa: E501
    assert covalent_result['to'] == web3_result['to'] == '0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106'  # noqa: E501
    assert covalent_result['gas'] == web3_result['gas'] == 195000
    assert covalent_result['gasPrice'] == web3_result['gasPrice'] == 225000000000
