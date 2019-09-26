import pytest

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history import limit_trade_list_to_period
from rotkehlchen.tests.utils.constants import ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3
from rotkehlchen.tests.utils.history import TEST_END_TS, mock_history_processing_and_exchanges
from rotkehlchen.typing import Location, SupportedBlockchain, TradeType


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_history_creation(
        rotkehlchen_server_with_exchanges,
        accountant,
):
    """This is a big test that contacts all exchange mocks and returns mocked
    trades and other data from exchanges in order to create the accounting history
    for a specific period and see that rotkehlchen handles the creation of that
    history correctly

    The actual checking happens in:
    rotkehlchen.tests.utils.history.check_result_of_history_creation()
    """
    server = rotkehlchen_server_with_exchanges
    rotki = server.rotkehlchen
    rotki.accountant = accountant

    kraken = rotki.exchange_manager.connected_exchanges['kraken']
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    # Let's add 3 blockchain accounts
    rotki.data.db.add_blockchain_account(SupportedBlockchain.ETHEREUM, ETH_ADDRESS1)
    rotki.data.db.add_blockchain_account(SupportedBlockchain.ETHEREUM, ETH_ADDRESS2)
    rotki.data.db.add_blockchain_account(SupportedBlockchain.ETHEREUM, ETH_ADDRESS3)
    (
        accountant_patch,
        polo_patch,
        binance_patch,
        bittrex_patch,
        bitmex_patch,
        etherscan_patch,
    ) = mock_history_processing_and_exchanges(rotki)
    with accountant_patch, polo_patch, binance_patch, bittrex_patch, bitmex_patch, etherscan_patch:
        response = server.process_trade_history(start_ts='0', end_ts=str(TEST_END_TS))
    # The history processing is completely mocked away and omitted in this test.
    # because it is only for the history creation not its processing.
    # For history processing tests look at test_accounting.py and
    # test_accounting_events.py
    assert response['message'] == ''
    assert response['result'] == {}

    # And now make sure that warnings have also been generated for the query of
    # the unsupported/unknown assets
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 13
    assert 'kraken trade with unknown asset IDONTEXISTTOO' in warnings[0]
    assert 'unknown kraken asset IDONTEXIST. Ignoring its deposit/withdrawals query' in warnings[1]
    msg = 'unknown kraken asset IDONTEXISTEITHER. Ignoring its deposit/withdrawals query'
    assert msg in warnings[2]
    assert 'poloniex trade with unknown asset NOEXISTINGASSET' in warnings[3]
    assert 'poloniex trade with unsupported asset BALLS' in warnings[4]
    assert 'withdrawal of unknown poloniex asset IDONTEXIST' in warnings[5]
    assert 'withdrawal of unsupported poloniex asset DIS' in warnings[6]
    assert 'deposit of unknown poloniex asset IDONTEXIST' in warnings[7]
    assert 'deposit of unsupported poloniex asset EBT' in warnings[8]
    assert 'poloniex loan with unsupported asset BDC' in warnings[9]
    assert 'poloniex loan with unknown asset NOTEXISTINGASSET' in warnings[10]
    assert 'bittrex trade with unsupported asset PTON' in warnings[11]
    assert 'bittrex trade with unknown asset IDONTEXIST' in warnings[12]

    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 3
    assert 'kraken trade with unprocessable pair IDONTEXISTZEUR' in errors[0]
    assert 'kraken trade with unprocessable pair %$#%$#%$#%$#%$#%' in errors[1]
    assert 'bittrex trade with unprocessable pair %$#%$#%#$%' in errors[2]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_history_creation_remote_errors(
        rotkehlchen_server_with_exchanges,
        accountant,
):
    """Test that during history creation, remote errors are detected and errors are returned"""
    server = rotkehlchen_server_with_exchanges
    rotki = server.rotkehlchen
    rotki.accountant = accountant
    kraken = rotki.exchange_manager.connected_exchanges['kraken']
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.remote_errors = True
    (
        accountant_patch,
        polo_patch,
        binance_patch,
        bittrex_patch,
        bitmex_patch,
        etherscan_patch,
    ) = mock_history_processing_and_exchanges(rotki, remote_errors=True)
    with accountant_patch, polo_patch, binance_patch, bittrex_patch, bitmex_patch, etherscan_patch:
        response = server.process_trade_history(start_ts='0', end_ts=str(TEST_END_TS))
    # The history processing is completely mocked away and omitted in this test.
    # because it is only for the history creation not its processing.
    # For history processing tests look at test_accounting.py and
    # test_accounting_events.py
    assert 'invalid JSON' in response['message']
    assert 'Binance' in response['message']
    assert 'Bittrex' in response['message']
    assert 'Bitmex' in response['message']
    assert 'Kraken' in response['message']
    assert 'Poloniex' in response['message']
    assert response['result'] == {}


def test_limit_trade_list_to_period():
    trade1 = Trade(
        timestamp=1459427707,
        location=Location.KRAKEN,
        pair='ETH_BTC',
        trade_type=TradeType.BUY,
        amount=FVal(1),
        rate=FVal(1),
        fee=FVal('0.1'),
        fee_currency=A_ETH,
        link='id1',
    )
    trade2 = Trade(
        timestamp=1469427707,
        location=Location.POLONIEX,
        pair='ETH_BTC',
        trade_type=TradeType.BUY,
        amount=FVal(1),
        rate=FVal(1),
        fee=FVal('0.1'),
        fee_currency=A_ETH,
        link='id2',
    )
    trade3 = Trade(
        timestamp=1479427707,
        location=Location.POLONIEX,
        pair='ETH_BTC',
        trade_type=TradeType.BUY,
        amount=FVal(1),
        rate=FVal(1),
        fee=FVal('0.1'),
        fee_currency=A_ETH,
        link='id3',
    )

    full_list = [trade1, trade2, trade3]
    assert limit_trade_list_to_period(full_list, 1459427706, 1479427708) == full_list
    assert limit_trade_list_to_period(full_list, 1459427707, 1479427708) == full_list
    assert limit_trade_list_to_period(full_list, 1459427707, 1479427707) == full_list

    expected = [trade2, trade3]
    assert limit_trade_list_to_period(full_list, 1459427708, 1479427707) == expected
    expected = [trade2]
    assert limit_trade_list_to_period(full_list, 1459427708, 1479427706) == expected
    assert limit_trade_list_to_period(full_list, 0, 10) == []
    assert limit_trade_list_to_period(full_list, 1479427708, 1479427719) == []
    assert limit_trade_list_to_period([trade1], 1459427707, 1459427707) == [trade1]
    assert limit_trade_list_to_period([trade2], 1469427707, 1469427707) == [trade2]
    assert limit_trade_list_to_period([trade3], 1479427707, 1479427707) == [trade3]
    assert limit_trade_list_to_period(full_list, 1459427707, 1459427707) == [trade1]
    assert limit_trade_list_to_period(full_list, 1469427707, 1469427707) == [trade2]
    assert limit_trade_list_to_period(full_list, 1479427707, 1479427707) == [trade3]
