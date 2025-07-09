__all__ = [
    'MODULE_NAME_TO_PATH',
]

# to avoid circular imports all the paths are moved in a mapping here
MODULE_NAME_TO_PATH = {
    'nfts': '.nft.nfts',
    'eth2': '.eth2.eth2',
    'compound': '.compound.compound',
    'sushiswap': '.sushiswap.sushiswap',
    'uniswap': '.uniswap.uniswap',
    'loopring': '.l2.loopring',
    'liquity': '.liquity.trove',
    'makerdao_dsr': '.makerdao.dsr',
    'makerdao_vaults': '.makerdao.vaults',
    'pickle_finance': '.pickle_finance.main',
}
