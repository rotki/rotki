from rotkehlchen.constants.resolver import strethaddress_to_identifier

KNOWN_ETH_SPAM_TOKENS = [
    # khex.net and said to be spam by etherscan
    strethaddress_to_identifier('0x4AF9ab04615cB91e2EE8cbEDb43fb52eD205041B'),
    # erc token, seems to be a spam token
    strethaddress_to_identifier('0x78d9A9355a7823887868492c47368956ea473618'),
    # yLiquidate (YQI) seems to be a scam
    strethaddress_to_identifier('0x3d3d5cCE38afb7a379B2C3175Ee56e2dC72CD7C8'),
    # Old kick token
    strethaddress_to_identifier('0xC12D1c73eE7DC3615BA4e37E4ABFdbDDFA38907E'),
    # kick token
    strethaddress_to_identifier('0x824a50dF33AC1B41Afc52f4194E2e8356C17C3aC'),
    # Fake gear token
    strethaddress_to_identifier('0x6D38b496dCc9664C6908D8Afba6ff926887Fc359'),
    # EthTrader Contribution (CONTRIB) few txs and all failed
    strethaddress_to_identifier('0xbe1fffB262a2C3e65c5eb90f93caf4eDC7d28c8d'),
    # a68.net pishing/hack
    strethaddress_to_identifier('0x1412ECa9dc7daEf60451e3155bB8Dbf9DA349933'),
    # akswap.io
    strethaddress_to_identifier('0x82dfDB2ec1aa6003Ed4aCBa663403D7c2127Ff67'),
    # up1 pishing token
    strethaddress_to_identifier('0xF9d25EB4C75ed744596392cf89074aFaA43614a8'),
    # deapy.org scam token
    strethaddress_to_identifier('0x01454cdC3FAb2a026CC7d1CB2aEa9B909D5bA0EE'),
]
