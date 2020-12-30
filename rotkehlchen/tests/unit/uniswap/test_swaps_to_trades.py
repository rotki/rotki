def test_empty_list(mock_uniswap):
    """Test passing empty list of swaps returns empty list
    """
    assert mock_uniswap.swaps_to_trades([]) == []
