from rotkehlchen.externalapis.cowswap import CowswapAPI
from rotkehlchen.types import SupportedBlockchain


def test_get_data_from_database(database):
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute("INSERT INTO cowswap_orders(identifier, order_type, raw_fee_amount) VALUES ('TEST_ORDER', 'market', 12345678)")  # noqa: E501

    assert CowswapAPI(
        database=database,
        chain=SupportedBlockchain.ETHEREUM,
    ).get_order_data('TEST_ORDER') == (12345678, 'market')
