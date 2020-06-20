from rotkehlchen.chain.ethereum.manager import EthereumManager


def test_ens_lookup_etherscan(etherscan, messages_aggregator):
    """Test that ENS lookup works when we use etherscan"""
    ethereum = EthereumManager(
        ethrpc_endpoint='',
        etherscan=etherscan,
        msg_aggregator=messages_aggregator,
        attempt_connect=False,
    )
    result = ethereum.ens_lookup('api.zerion.eth')
    __import__("pdb").set_trace()

    result = ethereum.ens_lookup('rotki.eth')
    assert result == '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    result = ethereum.ens_lookup('ishouldprobablynotexist.eth')
    assert result is None


def test_ens_lookup_node(etherscan, messages_aggregator):
    """Test that ENS lookup works when we use a node. Use blockscout's open node"""
    ethereum = EthereumManager(
        ethrpc_endpoint='https://mainnet-nethermind.blockscout.com',
        etherscan=etherscan,
        msg_aggregator=messages_aggregator,
        attempt_connect=True,
    )
    result = ethereum.ens_lookup('api.zerion.eth')
    result = ethereum.ens_lookup('rotki.eth')
    assert result == '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    result = ethereum.ens_lookup('ishouldprobablynotexist.eth')
    assert result is None
