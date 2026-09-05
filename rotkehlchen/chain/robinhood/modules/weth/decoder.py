from rotkehlchen.chain.arbitrum_one.modules.weth.decoder import WethDecoder as ArbitrumWethDecoder


class WethDecoder(ArbitrumWethDecoder):
    """WETH on Robinhood chain is the Arbitrum token bridge's proxy WETH. It emits no
    Deposit/Withdrawal logs, only mint/burn Transfers to and from the zero address, so
    the Arbitrum One decoder logic applies unchanged."""
