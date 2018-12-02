from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process

DUMMY_HASH = '0x0'
DUMMY_ADDRESS = '0x0'

trades_history = [
    {
        "timestamp": 1446979735,  # 08/11/2015
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 268.678317859,
        "cost": 1343.3915893,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "BTC",
        "amount": 5,
        "location": "external",
    }, {
        "timestamp": 1446979735,  # 08/11/2015
        "pair": "ETH_EUR",
        "type": "buy",
        "rate": 0.2315893,
        "cost": 335.804485,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "ETH",
        "amount": 1450,
        "location": "external",
    }, {
        'timestamp': 1467378304,  # 31/06/2016
        'pair': 'BTC_EUR',  # cryptocompare hourly BTC/EUR price 612.45
        'type': 'sell',
        'rate': 612.45,
        'cost': 1531.125,
        'cost_currency': 'EUR',
        'fee': '0.15',
        'fee_currency': 'EUR',
        'amount': 2.5,
        'location': 'kraken',
    }, {
        "timestamp": 1473505138,  # 10/09/2016
        "pair": "BTC_ETH",  # cryptocompare hourly ETH/EUR price: 10.365
        "type": "buy",  # Buy ETH with BTC -- taxable (within 1 year)
        "rate": 0.01858275,  # cryptocompare hourly BTC/EUR price: 556.435
        "cost": 0.9291375,
        "cost_currency": "BTC",
        "fee": 0.06999999999999999,
        "fee_currency": "ETH",
        "amount": 50.0,
        "location": "poloniex"
    }, {
        "timestamp": 1475042230,  # 28/09/2016
        "pair": "BTC_ETH",  # cryptocompare hourly ETH/EUR price: 11.925
        "type": "sell",  # Sell ETH for BTC -- taxable (within 1 year)
        "rate": 0.02209898,  # cryptocompare hourly BTC/EUR price: 537.805
        "cost": 0.5524745,
        "cost_currency": "BTC",
        "fee": 0.001,
        "fee_currency": "ETH",
        "amount": 25.0,
        "location": "poloniex",
    }, {
        "timestamp": 1476536704,  # 15/10/2016
        "pair": "BTC_ETH",  # cryptocompare hourly ETH/EUR price: 10.775
        "type": "sell",  # Sell ETH for BTC -- taxable (within 1 year)
        "rate": 0.018355,  # cryptocompare hourly BTC/EUR price: 585.96
        "cost": 3.3039,
        "cost_currency": "BTC",
        "fee": 0.01,
        "fee_currency": "ETH",
        "amount": 180.0,
        "location": "poloniex"
    }, {
        "timestamp": 1479200704,  # 15/11/2016
        "pair": "DASH_BTC",  # cryptocompare hourly DASH/EUR price: 8.9456
        "type": "buy",  # Buy DASH with BTC -- non taxable (after 1 year)
        "rate": 0.0134,  # cryptocompare hourly BTC/EUR price: 667.185
        "cost": 0.536,
        "cost_currency": "BTC",
        "fee": 0.00082871175,
        "fee_currency": "BTC",
        "amount": 40,
        "location": "poloniex"
    }, {  # settlement loss but outside query period
        "timestamp": 1480683904,  # 02/12/2016
        "pair": "DASH_BTC",  # cryptocompare hourly DASH/EUR price: 8.104679571509114828039
        "type": "settlement_sell",  # settlement sell DASH for BTC -- taxable (within 1 year)
        "rate": 0.011265,  # cryptocompare hourly BTC/EUR price: 723.505
        "cost": 0.00146445,
        "cost_currency": "BTC",
        "fee": 0.005,
        "fee_currency": "DASH",
        "amount": 0.13,
        "location": "poloniex"
    }, {  # 129.2517-0.01 - ((0.536-0.00082871175)*10/40)*667.185 = 39.9771360119
        "timestamp": 1483520704,  # 04/01/2017
        "pair": "DASH_EUR",  # cryptocompare hourly DASH/EUR price: 12.92517
        "type": "sell",  # Sell DASH for EUR -- taxable (within 1 year)
        "rate": 12.92517,
        "cost": 129.2517,
        "cost_currency": "EUR",
        "fee": 0.01,
        "fee_currency": "EUR",
        "amount": 10,
        "location": "kraken"
    }, {  # 0.00244725 * 942.78 + 0.01*15.36169816590634019 = 2.46083533666
        "timestamp": 1486299904,  # 05/02/2017
        "pair": "DASH_BTC",  # cryptocompare hourly DASH/EUR price: 15.36169816590634019
        "type": "settlement_sell",  # settlement sell DASH for BTC -- taxable (within 1 year)
        "rate": 0.016315,  # cryptocompare hourly BTC/EUR price: 942.78
        "cost": 0.00244725,
        "cost_currency": "BTC",
        "fee": 0.01,
        "fee_currency": "DASH",
        "amount": 0.15,
        "location": "poloniex"
    }
]

loans_list = [
    {  # outside query period -- should not matter
        'open_time': 1463505138,
        'close_time': 1463508234,  # 17/05/2016
        'currency': 'ETH',  # cryptocompare hourly ETH/EUR: 10.785
        'fee': FVal(0.000001),
        'earned': FVal(0.0002),
        'amount_lent': FVal(2),
    }, {  # (0.002-0.0001) * 10.9698996 = 0.02084280924
        'open_time': 1483350000,
        'close_time': 1483351504,  # 02/01/2017
        'currency': 'DASH',  # cryptocompare hourly DASH/EUR: 10.9698996
        'fee': FVal(0.0001),
        'earned': FVal(0.002),
        'amount_lent': FVal(2),
    }, {  # (0.003-0.00015)*13.22106438 = 0.037680033483
        'open_time': 1485250000,
        'close_time': 1485252304,  # 24/01/2017
        'currency': 'DASH',  # cryptocompare hourly DASH/EUR: 13.22106438
        'fee': FVal(0.00015),
        'earned': FVal(0.003),
        'amount_lent': FVal(2),
    }, {  # (0.0035-0.00011)*15.73995672 = 0.0533584532808
        'open_time': 1487021001,
        'close_time': 1487027104,  # 13/02/2017
        'currency': 'DASH',  # cryptocompare hourly DASH/EUR: 15.73995672
        'fee': FVal(0.00011),
        'earned': FVal(0.0035),
        'amount_lent': FVal(2),
    }, {  # outside query period -- should not matter
        'open_time': 1520113204,
        'close_time': 1520118304,  # 03/03/2018
        'currency': 'DASH',  # cryptocompare hourly DASH/EUR: 475.565
        'fee': FVal(0.0001),
        'earned': FVal(0.0025),
        'amount_lent': FVal(2),
    }
]

asset_movements_list = [
    {  # outside query period -- should not matter
        'exchange': 'kraken',
        'category': 'withdrawal',
        'timestamp': 1479510304,  # 18/11/2016,
        'asset': 'ETH',
        'amount': 95,
        'fee': 0.001,
    }, {  # 0.0087*52.885 = 0.4600995
        'exchange': 'kraken',
        'category': 'withdrawal',
        'timestamp': 1493291104,  # 27/04/2017,
        'asset': 'ETH',  # cryptocompare hourly ETH/EUR: 52.885
        'amount': 125,
        'fee': 0.0087,
    }, {  # deposit have no effect
        'exchange': 'kraken',
        'category': 'deposit',
        'timestamp': 1493636704,  # 01/05/2017,
        'asset': 'EUR',
        'amount': 750,
        'fee': 0,
    }, {  # 0.00029*1964.685 = 0.56975865
        'exchange': 'poloniex',
        'category': 'withdrawal',
        'timestamp': 1495969504,  # 28/05/2017,
        'asset': 'BTC',  # cryptocompare hourly BTC/EUR: 1964.685
        'amount': 8.5,
        'fee': 0.00029,
    }, {  # 0.0078*173.77 = 1.355406
        'exchange': 'poloniex',
        'category': 'withdrawal',
        'timestamp': 1502715904,  # 14/08/2017,
        'asset': 'DASH',  # cryptocompare hourly DASH/EUR: 173.77
        'amount': 20,
        'fee': 0.0078,
    }, {  # outside query period -- should not matter
        'exchange': 'bittrex',
        'category': 'withdrawal',
        'timestamp': 1517663104,  # 03/02/2018,
        'asset': 'ETH',
        'amount': 120,
        'fee': 0.001,
    }
]

eth_tx_list = [
    {  # outside query period -- should not matter
        'timestamp': 1463184190,  # 14/05/2016
        'block_number': 1512689,
        'hash': DUMMY_HASH,
        'from_address': DUMMY_ADDRESS,
        'to_address': DUMMY_ADDRESS,
        'value': 12323,
        'gas': 5000000,
        'gas_price': 2000000000,
        'gas_used': 25000000,
    }, {  # ((2000000000 * 1000000) / (10 ** 18)) * 47.5 = 0.095
        'timestamp': 1491062063,  # 01/04/2017
        'block_number': 3458409,  # cryptocompare hourly ETH/EUR: 47.5
        'hash': DUMMY_HASH,
        'from_address': DUMMY_ADDRESS,
        'to_address': DUMMY_ADDRESS,
        'value': 12323,
        'gas': 5000000,
        'gas_price': 2000000000,
        'gas_used': 1000000,
    }, {  # ((2200000000 * 2500000) / (10 ** 18)) * 393.955 = 2.1667525
        'timestamp': 1511626623,  # 25/11/2017
        'block_number': 4620323,  # cryptocompare hourly ETH/EUR: 393.955
        'hash': DUMMY_HASH,
        'from_address': DUMMY_ADDRESS,
        'to_address': DUMMY_ADDRESS,
        'value': 12323,
        'gas': 5000000,
        'gas_price': 2200000000,
        'gas_used': 2500000,
    }, {  # outside query period -- should not matter
        'timestamp': 1523399409,  # 10/04/2018
        'block_number': 5417790,
        'hash': DUMMY_HASH,
        'from_address': DUMMY_ADDRESS,
        'to_address': DUMMY_ADDRESS,
        'value': 12323,
        'gas': 5000000,
        'gas_price': 2100000000,
        'gas_used': 1900000,
    }
]


def test_end_to_end_tax_report(accountant):
    result = accounting_history_process(
        accountant=accountant,
        start_ts=1483228800,  # 01/01/2017
        end_ts=1514764799,  # 31/12/2017
        history_list=trades_history,
        loans_list=loans_list,
        asset_movements_list=asset_movements_list,
        eth_transaction_list=eth_tx_list,
    )
    result = result['overview']
    general_trade_pl = FVal(result['general_trade_profit_loss'])
    assert general_trade_pl.is_close("39.977136")
    taxable_trade_pl = FVal(result['taxable_trade_profit_loss'])
    assert taxable_trade_pl.is_close("39.977136")
    loan_profit = FVal(result['loan_profit'])
    assert loan_profit.is_close("0.111881296004")
    settlement_losses = FVal(result['settlement_losses'])
    assert settlement_losses.is_close('2.46083533666')
    asset_movement_fees = FVal(result['asset_movement_fees'])
    assert asset_movement_fees.is_close("2.38526415")
    ethereum_transaction_gas_costs = FVal(result['ethereum_transaction_gas_costs'])
    assert ethereum_transaction_gas_costs.is_close("2.2617525")
    expected_total_taxable_pl = (
        taxable_trade_pl +
        loan_profit -
        settlement_losses -
        asset_movement_fees -
        ethereum_transaction_gas_costs
    )
    total_taxable_pl = FVal(result['total_taxable_profit_loss'])
    assert expected_total_taxable_pl.is_close(total_taxable_pl)
    expected_total_pl = (
        general_trade_pl +
        loan_profit -
        settlement_losses -
        asset_movement_fees -
        ethereum_transaction_gas_costs
    )
    total_pl = FVal(result['total_taxable_profit_loss'])
    assert expected_total_pl.is_close(total_pl)
