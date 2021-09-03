import pytest

from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.transactions import EthTransactions
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.tests.utils.ethereum import ETHERSCAN_AND_INFURA_PARAMS
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction, Timestamp
from rotkehlchen.utils.misc import hexstring_to_bytes


@pytest.mark.parametrize(*ETHERSCAN_AND_INFURA_PARAMS)
def test_get_transaction_receipt(database, ethereum_manager, call_order):  # pylint: disable=unused-argument  # noqa: E501
    """Test that getting a transaction receipt from the network and saving it in theDB works"""
    dbethtx = DBEthTx(database)
    tx_hash = '0x692f9a6083e905bdeca4f0293f3473d7a287260547f8cbccc38c5cb01591fcda'
    tx_hash_b = hexstring_to_bytes(tx_hash)
    input_data_b = hexstring_to_bytes('0x7ff36ab5000000000000000000000000000000000000000000000367469995d0723279510000000000000000000000000000000000000000000000000000000000000080000000000000000000000000443e1f9b1c866e54e914822b7d3d7165edb6e9ea00000000000000000000000000000000000000000000000000000000612ff9b50000000000000000000000000000000000000000000000000000000000000002000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000002a3bff78b79a009976eea096a51a948a3dc00e34')  # noqa: E501
    transaction = EthereumTransaction(
        tx_hash=tx_hash_b,
        timestamp=Timestamp(1630532276),
        block_number=13142218,
        from_address=ChecksumEthAddress('0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea'),
        to_address=ChecksumEthAddress('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        value=10 * 10**18,
        gas=194928,
        gas_price=0.000000204 * 10**18,
        gas_used=136675,
        input_data=input_data_b,
        nonce=13,
    )
    dbethtx.add_ethereum_transactions(ethereum_transactions=[transaction])

    expected_receipt = EthereumTxReceipt(
        tx_hash=tx_hash_b,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=295,
                data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8a\xc7#\x04\x89\xe8\x00\x00',  # noqa: E501
                address=ChecksumEthAddress('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=['0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d', '0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'],  # noqa: E501
            ), EthereumTxReceiptLog(
                log_index=296,
                data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8a\xc7#\x04\x89\xe8\x00\x00',  # noqa: E501
                address=ChecksumEthAddress('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=['0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d', '0x000000000000000000000000caa004418eb42cdf00cb057b7c9e28f0ffd840a5', '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'],   # noqa: E501
            ), EthereumTxReceiptLog(
                log_index=297,
                data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03k\xa1\xd5;\xae\xed\xa5\xed ',  # noqa: E501
                address=ChecksumEthAddress('0x2a3bFF78B79A009976EeA096a51A948a3dC00e34'),
                removed=False,
                topics=['0x000000000000000000000000443e1f9b1c866e54e914822b7d3d7165edb6e9ea', '0x000000000000000000000000caa004418eb42cdf00cb057b7c9e28f0ffd840a5', '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'],  # noqa: E501
            ), EthereumTxReceiptLog(
                log_index=298,
                data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00{n\xa03\x18\x9b\xa7\xd0G\xe3\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x14\x0b\xc8\x19M\xd0\xf5\xe4\xbe',  # noqa: E501
                address=ChecksumEthAddress('0xcaA004418eB42cdf00cB057b7C9E28f0FfD840a5'),
                removed=False,
                topics=['0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'],
            ), EthereumTxReceiptLog(
                log_index=299,
                data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8a\xc7#\x04\x89\xe8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03k\xa1\xd5;\xae\xed\xa5\xed \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',  # noqa: E501
                address=ChecksumEthAddress('0xcaA004418eB42cdf00cB057b7C9E28f0FfD840a5'),
                removed=False,
                topics=['0x000000000000000000000000443e1f9b1c866e54e914822b7d3d7165edb6e9ea', '0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d', '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'],  # noqa: E501
            ),
        ],
    )

    txmodule = EthTransactions(ethereum=ethereum_manager, database=database)
    receipt = txmodule.get_transaction_receipt(tx_hash)
    assert receipt == expected_receipt
