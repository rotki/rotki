from rotkehlchen.externalapis.cowswap import CowswapAPI, parse_order_data
from rotkehlchen.types import SupportedBlockchain


def test_get_data_from_database(database):
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute("INSERT INTO cowswap_orders(identifier, order_type, raw_fee_amount) VALUES ('TEST_ORDER', 'market', 12345678)")  # noqa: E501

    assert CowswapAPI(
        database=database,
        chain=SupportedBlockchain.ETHEREUM,
    ).get_order_data('TEST_ORDER') == (12345678, 'market')


def test_handles_missing_fullappdata():
    # Data taken from https://api.cow.fi/xdai/api/v1/orders/0x246d4707213a3d4bab8e7cae568cb458b81b3a9f05c014c1b6f7b537c788b5205089007dec8e93f891dcb908c9e2af8d9dedb72e68d95aa4  noqa: E501
    order_data = {
        "creationDate":"2025-09-28T15:51:30Z",
        "owner":"0x5089007dec8e93f891dcb908c9e2af8d9dedb72e",
        "uid":"0x246d4707213a3d4bab8e7cae568cb458b81b3a9f05c014c1b6f7b537c788b5205089007dec8e93f891dcb908c9e2af8d9dedb72e68d95aa4",
        "availableBalance": None,
        "executedBuyAmount":"55114502215468646",
        "executedSellAmount":"223917127089608233961",
        "executedSellAmountBeforeFees":"223917127089608233961",
        "executedFeeAmount":"0",
        "executedFee":"589857233861541",
        "executedFeeToken":"0xaf204776c7245bf4147c2612bf6e5972ee483701",
        "invalidated": False,
        "status":"fulfilled",
        "class":"liquidity",
        "settlementContract":"0x9008d19f58aabd9ed0d60971565aa8510560ab41",
        "isLiquidityOrder": True,
        "fullAppData": None,
        "sellToken":"0xaf204776c7245bf4147c2612bf6e5972ee483701",
        "buyToken":"0x6c76971f98945ae98dd7d4dfca8711ebea946ea6",
        "receiver":"0x0000000000000000000000000000000000000000",
        "sellAmount":"223917127089608233961",
        "buyAmount":"55103055357127186",
        "validTo":1759074980,
        "appData":"0x362e5182440b52aa8fffe70a251550fbbcbca424740fe5a14f59bf0c1b06fe1d",
        "feeAmount":"0",
        "kind":"sell",
        "partiallyFillable": False,
        "sellTokenBalance":"erc20",
        "buyTokenBalance":"erc20",
        "signingScheme":"eip1271",
        "signature":"0x5089007dec8e93f891dcb908c9e2af8d9dedb72e000000000000000000000000af204776c7245bf4147c2612bf6e5972ee4837010000000000000000000000006c76971f98945ae98dd7d4dfca8711ebea946ea6000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c237970b9661893e900000000000000000000000000000000000000000000000000c3c3efd899aa120000000000000000000000000000000000000000000000000000000068d95aa4362e5182440b52aa8fffe70a251550fbbcbca424740fe5a14f59bf0c1b06fe1d0000000000000000000000000000000000000000000000000000000000000000f3b277728b3fee749481eb3e0b3b48980dbbab78658fc419025cb16eee34677500000000000000000000000000000000000000000000000000000000000000005a28e9363bb942b639270062aa6bb295f434bcdfc42c97267bf003f272060dc95a28e9363bb942b639270062aa6bb295f434bcdfc42c97267bf003f272060dc9",
        "interactions": {
            "pre":[],
            "post":[]
        }
    }
    assert parse_order_data(order_data) == (589857233861541, 'limit')
