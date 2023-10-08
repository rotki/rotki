from contextlib import nullcontext
from unittest.mock import patch

from web3.datastructures import AttributeDict

from rotkehlchen.types import deserialize_evm_tx_hash
from rotkehlchen.utils.hexbytes import HexBytes

covalent_tx_receipt_result = {
    'block_height': 2716404,
    'block_signed_at': '2021-07-19T21:49:58Z',
    'fees_paid': '29086200000000000',
    'from_address': '0x4f59ae4374d93b7087f2afa6db95815b43d1c2da',
    'from_address_label': None,
    'gas_offered': 195000,
    'gas_price': 225000000000,
    'gas_quote': 0.3087283978471756,
    'gas_quote_rate': 10.614256858825684,
    'gas_spent': 129272,
    'log_events': [{'block_height': 2716404,
                    'block_signed_at': '2021-07-19T21:49:58Z',
                    'decoded': {
                        'name': 'Swap',
                        'params': [
                            {'decoded': True, 'indexed': True, 'name': 'sender', 'type': 'address', 'value': '0xe54ca86531e17ef3616d22ca28b0d458b6c89106'},  # noqa: E501
                            {'decoded': True, 'indexed': False, 'name': 'amount0In', 'type': 'uint256', 'value': '115951490920000000000'},  # noqa: E501
                            {'decoded': True, 'indexed': False, 'name': 'amount1In', 'type': 'uint256', 'value': '0'},  # noqa: E501
                            {'decoded': True, 'indexed': False, 'name': 'amount0Out', 'type': 'uint256', 'value': '0'},  # noqa: E501
                            {'decoded': True, 'indexed': False, 'name': 'amount1Out', 'type': 'uint256', 'value': '1173514056'},  # noqa: E501
                            {'decoded': True, 'indexed': True, 'name': 'to', 'type': 'address', 'value': '0x4f59ae4374d93b7087f2afa6db95815b43d1c2da'},  # noqa: E501
                        ],
                        'signature': 'Swap(indexed address sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, indexed address to)'},  # noqa: E501
                    'log_offset': 9,
                    'raw_log_data': '0x000000000000000000000000000000000000000000000006492672a787881000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000045f26748',  # noqa: E501
                    'raw_log_topics': [
                        '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822',
                        '0x000000000000000000000000e54ca86531e17ef3616d22ca28b0d458b6c89106',
                        '0x0000000000000000000000004f59ae4374d93b7087f2afa6db95815b43d1c2da'],
                    'sender_address': '0x9ee0a4e21bd333a6bb2ab298194320b8daa26516',
                    'sender_address_label': None,
                    'sender_contract_decimals': 18,
                    'sender_contract_ticker_symbol': 'PGL',
                    'sender_logo_url': 'https://logos.covalenthq.com/tokens/43114/0x9ee0a4e21bd333a6bb2ab298194320b8daa26516.png',
                    'sender_name': 'Pangolin Liquidity',
                    'tx_hash': '0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d',  # noqa: E501
                    'tx_offset': 1},
                   {'block_height': 2716404,
                    'block_signed_at': '2021-07-19T21:49:58Z',
                    'decoded': {'name': 'Sync',
                                'params': [
                                    {'decoded': True, 'indexed': False, 'name': 'reserve0', 'type': 'uint112', 'value': '156407372466602947364673'},  # noqa: E501
                                    {'decoded': True, 'indexed': False, 'name': 'reserve1', 'type': 'uint112', 'value': '1586543339131'}],  # noqa: E501
                                'signature': 'Sync(uint112 reserve0, uint112 reserve1)'},
                    'log_offset': 8,
                    'raw_log_data': '0x00000000000000000000000000000000000000000000211edc53a099b0dbc74100000000000000000000000000000000000000000000000000000171655a267b',  # noqa: E501
                    'raw_log_topics': [
                        '0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1',
                    ],
                    'sender_address': '0x9ee0a4e21bd333a6bb2ab298194320b8daa26516',
                    'sender_address_label': None,
                    'sender_contract_decimals': 18,
                    'sender_contract_ticker_symbol': 'PGL',
                    'sender_logo_url': 'https://logos.covalenthq.com/tokens/43114/0x9ee0a4e21bd333a6bb2ab298194320b8daa26516.png',
                    'sender_name': 'Pangolin Liquidity',
                    'tx_hash': '0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d',  # noqa: E501
                    'tx_offset': 1},
                   {'block_height': 2716404,
                    'block_signed_at': '2021-07-19T21:49:58Z',
                    'decoded': {'name': 'Transfer',
                                'params': [
                                    {'decoded': True, 'indexed': True, 'name': 'from', 'type': 'address', 'value': '0x9ee0a4e21bd333a6bb2ab298194320b8daa26516'},  # noqa: E501
                                    {'decoded': True, 'indexed': True, 'name': 'to', 'type': 'address', 'value': '0x4f59ae4374d93b7087f2afa6db95815b43d1c2da'},  # noqa: E501
                                    {'decoded': True, 'indexed': False, 'name': 'value', 'type': 'uint256', 'value': '1173514056'}],  # noqa: E501
                                'signature': 'Transfer(indexed address from, indexed address to, uint256 value)'},  # noqa: E501
                    'log_offset': 7,
                    'raw_log_data': '0x0000000000000000000000000000000000000000000000000000000045f26748',  # noqa: E501
                    'raw_log_topics': [
                        '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
                        '0x0000000000000000000000009ee0a4e21bd333a6bb2ab298194320b8daa26516',
                        '0x0000000000000000000000004f59ae4374d93b7087f2afa6db95815b43d1c2da'],
                    'sender_address': '0xde3a24028580884448a5397872046a019649b084',
                    'sender_address_label': None,
                    'sender_contract_decimals': 6,
                    'sender_contract_ticker_symbol': 'USDT',
                    'sender_logo_url': 'https://logos.covalenthq.com/tokens/43114/0xde3a24028580884448a5397872046a019649b084.png',
                    'sender_name': 'Tether USD',
                    'tx_hash': '0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d',  # noqa: E501
                    'tx_offset': 1},
                   {'block_height': 2716404,
                    'block_signed_at': '2021-07-19T21:49:58Z',
                    'decoded': {'name': 'Transfer',
                                'params': [
                                    {'decoded': True, 'indexed': True, 'name': 'from', 'type': 'address', 'value': '0xe54ca86531e17ef3616d22ca28b0d458b6c89106'},  # noqa: E501
                                    {'decoded': True, 'indexed': True, 'name': 'to', 'type': 'address', 'value': '0x9ee0a4e21bd333a6bb2ab298194320b8daa26516'},  # noqa: E501
                                    {'decoded': True, 'indexed': False, 'name': 'value', 'type': 'uint256', 'value': '115951490920000000000'}],  # noqa: E501
                                'signature': 'Transfer(indexed address from, indexed address to, uint256 value)'},  # noqa: E501
                    'log_offset': 6,
                    'raw_log_data': '0x000000000000000000000000000000000000000000000006492672a787881000',  # noqa: E501
                    'raw_log_topics': [
                        '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
                        '0x000000000000000000000000e54ca86531e17ef3616d22ca28b0d458b6c89106',
                        '0x0000000000000000000000009ee0a4e21bd333a6bb2ab298194320b8daa26516'],
                    'sender_address': '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7',
                    'sender_address_label': None,
                    'sender_contract_decimals': 18,
                    'sender_contract_ticker_symbol': 'WAVAX',
                    'sender_logo_url': 'https://logos.covalenthq.com/tokens/0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7.png',
                    'sender_name': 'Wrapped AVAX',
                    'tx_hash': '0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d',  # noqa: E501
                    'tx_offset': 1},
                   {'block_height': 2716404,
                    'block_signed_at': '2021-07-19T21:49:58Z',
                    'decoded': {'name': 'Deposit',
                                'params': [
                                    {'decoded': True, 'indexed': True, 'name': 'dst', 'type': 'address', 'value': '0xe54ca86531e17ef3616d22ca28b0d458b6c89106'},  # noqa: E501
                                    {'decoded': True, 'indexed': False, 'name': 'wad', 'type': 'uint256', 'value': '115951490920000000000'}],  # noqa: E501
                                'signature': 'Deposit(indexed address dst, uint256 wad)'},
                    'log_offset': 5,
                    'raw_log_data': '0x000000000000000000000000000000000000000000000006492672a787881000',  # noqa: E501
                    'raw_log_topics': [
                        '0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c',
                        '0x000000000000000000000000e54ca86531e17ef3616d22ca28b0d458b6c89106'],
                    'sender_address': '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7',
                    'sender_address_label': None,
                    'sender_contract_decimals': 18,
                    'sender_contract_ticker_symbol': 'WAVAX',
                    'sender_logo_url': 'https://logos.covalenthq.com/tokens/0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7.png',
                    'sender_name': 'Wrapped AVAX',
                    'tx_hash': '0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d',  # noqa: E501
                    'tx_offset': 1}],
    'successful': True,
    'timestamp': 1626731398,
    'to_address': '0xe54ca86531e17ef3616d22ca28b0d458b6c89106',
    'to_address_label': None,
    'tx_hash': '0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d',
    'tx_offset': 1,
    'value': '115951490920000000000',
    'value_quote': 1230.738907788674,
}

web3_tx_receipt_result = AttributeDict({
    'blockHash': HexBytes('0x3ed1c9e40e6b07355e05683cf0078167149c95f00a81ecc2885896119a16fd1a'),
    'blockNumber': 2716404,
    'from': '0x4F59aE4374D93b7087F2aFa6Db95815b43d1C2dA',
    'gas': 195000,
    'gasPrice': 225000000000,
    'hash': HexBytes('0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d'),
    'input': '0xa2a1623d0000000000000000000000000000000000000000000000000000000045e2330c00000000000000000000000000000000000000000000000000000000000000800000000000000000000000004f59ae4374d93b7087f2afa6db95815b43d1c2da0000000000000000000000000000000000000000000000000000000060f5f8330000000000000000000000000000000000000000000000000000000000000002000000000000000000000000b31f66aa3c1e785363f0875a1b74e27b85fd66c7000000000000000000000000de3a24028580884448a5397872046a019649b084',  # noqa: E501
    'nonce': 35808,
    'to': '0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106',
    'transactionIndex': 1,
    'value': 115951490920000000000,
    'type': '0x0',
    'chainId': '0xa86a',
    'v': 86263,
    'r': HexBytes('0xe7a10b563221d5d3e19a9cb8b489d1c548dd1ce1a11969f9db246547c0540b61'),
    's': HexBytes('0x14f16512139c96884d72da842427d5e9802566a3651caa257431a6678dd6adae')})


def test_get_transaction_receipt(avalanche_manager, network_mocking):
    covalent_no_data_patch = patch.object(
        avalanche_manager.covalent,
        'get_transaction_receipt',
        side_effect=lambda *args: None,  # None means no data from covalent so we go to w3
    )
    covalent_patch = patch.object(
        avalanche_manager.covalent,
        'get_transaction_receipt',
        return_value=covalent_tx_receipt_result,
    ) if network_mocking else nullcontext()
    w3_patch = patch.object(
        avalanche_manager.w3.eth,
        'get_transaction',
        return_value=web3_tx_receipt_result,
    ) if network_mocking else nullcontext()

    tx_hash = deserialize_evm_tx_hash('0x7e7dee4b821331437524d0fd176a5090abbe4e857c849b06dfe9224f00e22f4d')  # noqa: E501
    with covalent_patch:
        covalent_result = avalanche_manager.get_transaction_receipt(tx_hash=tx_hash)
    with covalent_no_data_patch, w3_patch:
        web3_result = avalanche_manager.get_transaction_receipt(tx_hash=tx_hash)

    assert covalent_result['hash'] == web3_result['hash'] == tx_hash
    assert covalent_result['blockNumber'] == web3_result['blockNumber'] == 2716404
    assert covalent_result['from'] == web3_result['from'] == '0x4F59aE4374D93b7087F2aFa6Db95815b43d1C2dA'  # noqa: E501
    assert covalent_result['to'] == web3_result['to'] == '0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106'  # noqa: E501
    assert covalent_result['gas'] == web3_result['gas'] == 195000
    assert covalent_result['gasPrice'] == web3_result['gasPrice'] == 225000000000
