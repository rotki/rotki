import pytest

from rotkehlchen.externalapis.cowswap import CowswapAPI
from rotkehlchen.types import SupportedBlockchain


def test_get_data_from_database(database):
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute("INSERT INTO cowswap_orders(identifier, order_type, raw_fee_amount) VALUES ('TEST_ORDER', 'market', 12345678)")  # noqa: E501

    assert CowswapAPI(
        database=database,
        chain=SupportedBlockchain.ETHEREUM,
    ).get_order_data('TEST_ORDER') == (12345678, 'market')

@pytest.mark.vcr
def test_handles_missing_fullappdata(database):
    order_id = '0x246d4707213a3d4bab8e7cae568cb458b81b3a9f05c014c1b6f7b537c788b5205089007dec8e93f891dcb908c9e2af8d9dedb72e68d95aa4'
    assert CowswapAPI(
        database=database,
        chain=SupportedBlockchain.GNOSIS,
    ).get_order_data(order_id) == (589857233861541, 'limit')
