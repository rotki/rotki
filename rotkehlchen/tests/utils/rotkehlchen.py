from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.dbhandler import AssetBalance, LocationData
from rotkehlchen.tests.utils.constants import A_XMR
from rotkehlchen.typing import Timestamp


def add_starting_balances(datahandler):
    """Adds some starting balances to the a testing instance"""
    balances = [
        AssetBalance(
            time=Timestamp(1488326400),
            asset=A_BTC,
            amount='1',
            usd_value='1222.66',
        ),
        AssetBalance(
            time=Timestamp(1489326500),
            asset=A_XMR,
            amount='2',
            usd_value='33.8',
        ),
    ]
    datahandler.db.add_multiple_balances(balances)
    # Also add an unknown/invalid asset. This will generate a warning
    cursor = datahandler.db.conn.cursor()
    cursor.execute(
        'INSERT INTO timed_balances('
        '    time, currency, amount, usd_value) '
        ' VALUES(?, ?, ?, ?)',
        (1469326500, 'ADSADX', '10.1', '100.5'),
    )
    datahandler.db.conn.commit()

    location_data = [
        LocationData(
            time=Timestamp(1488326400),
            location='total',
            usd_value='1500.1',
        ), LocationData(
            time=Timestamp(1498326400),
            location='total',
            usd_value='1800.5',
        ),
        LocationData(
            time=Timestamp(1488326400),
            location='kraken',
            usd_value='150',
        ), LocationData(
            time=Timestamp(1498326400),
            location='kraken',
            usd_value='250.5',
        ),
    ]
    datahandler.db.add_multiple_location_data(location_data)
