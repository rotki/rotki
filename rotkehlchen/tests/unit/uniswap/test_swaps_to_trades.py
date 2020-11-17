def test_empty_list(uniswap_module):
    """Test passing empty list of swaps returns empty list
    """
    assert uniswap_module.swaps_to_trades([]) == []
