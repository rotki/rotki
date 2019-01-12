from rotkehlchen.fval import FVal

# Prices queried by cryptocompare  @ 12/01/2019
prices = {
    'BTC': {
        'EUR': {
            1446979735: FVal(355.9),
            1449809536: FVal(386.175),
            1464393600: FVal(422.9),
            1473505138: FVal(556.435),
            1473897600: FVal(542.87),
            1475042230: FVal(537.805),
            1476536704: FVal(585.96),
            1476979735: FVal(578.505),
            1479200704: FVal(667.185),
            1480683904: FVal(723.505),
            1484629704: FVal(810.49),
            1486299904: FVal(942.78),
            1487289600: FVal(979.39),
            1491177600: FVal(1039.935),
            1495969504: FVal(1964.685),
            1498694400: FVal(2244.255),
            1512693374: FVal(14415.365),
        },
    },
    'ETH': {
        'EUR': {
            1446979735: FVal(0.8583),
            1463184190: FVal(9.185),
            1463508234: FVal(10.785),
            1473505138: FVal(10.365),
            1475042230: FVal(11.925),
            1476536704: FVal(10.775),
            1479510304: FVal(8.915),
            1491062063: FVal(47.5),
            1493291104: FVal(52.885),
            1511626623: FVal(393.955),
        },
    },
    'XMR': {
        'EUR': {
            1449809536: FVal(0.396987900),  # BTC adjusted price
        },
    },
    'DASH': {
        'EUR': {
            # TODO: Switch to the DASH non-usd adjusted prices since cryptocompare
            # starting returning correct results and adjust the tests accordingly
            # 1479200704: FVal(9),
            1479200704: FVal(8.9456),  # old USD adjusted price

            # 1480683904: FVal(8.155),
            1480683904: FVal(8.104679571509114828039),  # old USD adjusted price

            # 1483351504: FVal(11.115),
            1483351504: FVal(10.9698996),  # old USD adjusted price

            # 1484629704: FVal(12.89),  # found in historical hourly
            1484629704: FVal(12.4625608386372145),  # old USD adjusted price

            # 1485252304: FVal(13.48),
            1485252304: FVal(13.22106438),  # old USD adjusted price

            # 1486299904: FVal(15.29),
            1486299904: FVal(15.36169816590634019),  # old USD adjusted price

            # 1487027104: FVal(16.08)
            1487027104: FVal(15.73995672),  # old USD adjusted price

            # 1502715904: FVal(173.035),
            1502715904: FVal(173.77),  # old USD adjusted price
        },
    },
}
