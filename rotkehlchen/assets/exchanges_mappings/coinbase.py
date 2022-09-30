from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import strethaddress_to_identifier

WORLD_TO_COINBASE = COMMON_ASSETS_MAPPINGS | {
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0x32353A6C91143bfd6C7d363B546e62a9A2489A20'): 'AGLD',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    strethaddress_to_identifier('0x4C19596f5aAfF459fA38B0f7eD92F11AE6543784'): 'TRU',
    strethaddress_to_identifier('0xa0246c9032bC3A600820415aE600c6388619A14D'): 'FARM',
    'STX-2': 'STX',
    strethaddress_to_identifier('0xec67005c4E498Ec7f55E092bd1d35cbC47C91892'): 'MLN',
    strethaddress_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB'): 'REP',
    strethaddress_to_identifier('0x362bc847A3a9637d3af6624EeC853618a43ed7D2'): 'PRQ',
    strethaddress_to_identifier('0x0258F474786DdFd37ABCE6df6BBb1Dd5dfC4434a'): 'ORN',
    strethaddress_to_identifier('0xdeFA4e8a7bcBA345F687a2f1456F5Edd9CE97202'): 'KNC',
    strethaddress_to_identifier('0x41D5D79431A913C4aE7d69a668ecdfE5fF9DFB68'): 'INV',
}
