from rotkehlchen.chain.ethereum.manager import NodeName

ETHEREUM_TEST_PARAMETERS = ['ethrpc_endpoint,ethereum_manager_connect_at_start', [
    # Query etherscan only
    ('', ()),
    # For "our own" node querying use infura
    ('https://mainnet.infura.io/v3/66302b8fb9874614905a3cbe903a0dbb', (NodeName.OWN,)),
]]
