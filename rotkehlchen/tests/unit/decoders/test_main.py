def test_decoders_initialization(evm_transaction_decoder):
    """Make sure that all decoders we have created are detected and initialized"""
    assert set(evm_transaction_decoder.decoders.keys()) == {
        'Aavev1',
        'Airdrops',
        'Compound',
        'Curve',
        'Dxdaomesa',
        'Ens',
        'Gitcoin',
        'Kyber',
        'Liquity',
        'Makerdao',
        'Oneinchv1',
        'Oneinchv2',
        'PickleFinance',
        'Uniswapv1',
        'Votium',
        'Zksync',
        'Hop',
    }
