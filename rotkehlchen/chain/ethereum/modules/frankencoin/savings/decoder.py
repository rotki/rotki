from rotkehlchen.chain.evm.decoding.frankencoin.savings.decoder import (
    FrankencoinSavingsCommonDecoder,
)


class FrankencoinsavingsDecoder(FrankencoinSavingsCommonDecoder):
    """Register the shared Frankencoin Savings decoder on Ethereum."""
