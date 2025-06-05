from http import HTTPStatus
from typing import Final
from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_BEST, A_ETH, A_EUR, A_USDT
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_ADA, A_AXS, A_LTC, A_TRY
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

WALLETS_RESPONSE = """{"data":[
{"type":"wallet","attributes":{"cryptocoin_id":"1","cryptocoin_symbol":"BTC","balance":"0.00000000","is_default":true,"name":"BTC Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"b52800aa-61f6-4251-a970-e53a864ebeaa"},
{"type":"wallet","attributes":{"cryptocoin_id":"3","cryptocoin_symbol":"LTC","balance":"0.00000000","is_default":true,"name":"LTC Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"6ab729ed-4983-44ba-ab54-2c30a20207ff"},
{"type":"wallet","attributes":{"cryptocoin_id":"5","cryptocoin_symbol":"ETH","balance":"100.55000000","is_default":true,"name":"ETH Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"184006fa-53de-4daa-89f2-637be3e40841"},
{"type":"wallet","attributes":{"cryptocoin_id":"6","cryptocoin_symbol":"LSK","balance":"0.00000000","is_default":true,"name":"LSK Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"d9ee40ec-9740-4c44-9c87-e181bd2638d2"},
{"type":"wallet","attributes":{"cryptocoin_id":"7","cryptocoin_symbol":"DASH","balance":"0.00000000","is_default":true,"name":"DASH Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"34100b3a-3566-48a2-8af4-43812b17d3cb"},
{"type":"wallet","attributes":{"cryptocoin_id":"8","cryptocoin_symbol":"XRP","balance":"0.00000000","is_default":true,"name":"XRP Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"6b69b07c-411a-446c-8c0d-256a9590c8cf"},
{"type":"wallet","attributes":{"cryptocoin_id":"9","cryptocoin_symbol":"BCH","balance":"0.00000000","is_default":true,"name":"BCH Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"f872b64c-f03e-4d85-b8cd-fb71d8da97ae"},
{"type":"wallet","attributes":{"cryptocoin_id":"11","cryptocoin_symbol":"PAN","balance":"0.00000000","is_default":true,"name":"PAN Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"7e3ec81e-1ff2-474d-be9c-3dcc44145cef"},
{"type":"wallet","attributes":{"cryptocoin_id":"12","cryptocoin_symbol":"KMD","balance":"0.00000000","is_default":true,"name":"KMD Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"9770202f-7ecb-4364-a661-a2cf323f9582"},
{"type":"wallet","attributes":{"cryptocoin_id":"13","cryptocoin_symbol":"MIOTA","balance":"0.00000000","is_default":true,"name":"MIOTA Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"438dff87-371d-40d1-82e4-1dd1adcbbbef"},
{"type":"wallet","attributes":{"cryptocoin_id":"14","cryptocoin_symbol":"EOS","balance":"0.00000000","is_default":true,"name":"EOS Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"491f1ede-0641-4417-bfb7-6a921f5dde67"},
{"type":"wallet","attributes":{"cryptocoin_id":"15","cryptocoin_symbol":"OMG","balance":"0.00000000","is_default":true,"name":"OMG Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"95e75440-7b5d-4c3b-95a4-b7e93e3f3b92"},
{"type":"wallet","attributes":{"cryptocoin_id":"16","cryptocoin_symbol":"REP","balance":"0.00000000","is_default":true,"name":"REP Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"ecc692f9-a653-4f6f-895f-b39425057a36"},
{"type":"wallet","attributes":{"cryptocoin_id":"17","cryptocoin_symbol":"ZRX","balance":"0.00000000","is_default":true,"name":"ZRX Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"7acd106a-0ada-4d7a-a553-a3df3f1e1daf"},
{"type":"wallet","attributes":{"cryptocoin_id":"18","cryptocoin_symbol":"ZEC","balance":"0.00000000","is_default":true,"name":"ZEC Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"a014059d-27a8-450f-8355-3e2660603b0c"},
{"type":"wallet","attributes":{"cryptocoin_id":"19","cryptocoin_symbol":"XEM","balance":"0.00000000","is_default":true,"name":"XEM Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"70e31845-8265-4fa3-8443-9f0c33394ad2"},
{"type":"wallet","attributes":{"cryptocoin_id":"20","cryptocoin_symbol":"XLM","balance":"0.00000000","is_default":true,"name":"XLM Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"02f85dc7-ff1d-4fcf-99d6-0e089d41cbf6"},
{"type":"wallet","attributes":{"cryptocoin_id":"21","cryptocoin_symbol":"XTZ","balance":"0.00000000","is_default":true,"name":"XTZ Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"27096c16-be41-43b1-9ee0-a8549cc0eb0f"},
{"type":"wallet","attributes":{"cryptocoin_id":"22","cryptocoin_symbol":"ADA","balance":"0.00000000","is_default":true,"name":"ADA Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"da42cac5-3363-45e8-9df4-408d421eb7ae"},
{"type":"wallet","attributes":{"cryptocoin_id":"23","cryptocoin_symbol":"NEO","balance":"0.00000000","is_default":true,"name":"NEO Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"d0afa8a7-dee9-44a7-9a9d-47d9d42d1dc9"},
{"type":"wallet","attributes":{"cryptocoin_id":"24","cryptocoin_symbol":"ETC","balance":"0.00000000","is_default":true,"name":"ETC Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"a0b3aa78-6a77-4778-9443-fb6280e38efa"},
{"type":"wallet","attributes":{"cryptocoin_id":"25","cryptocoin_symbol":"LINK","balance":"0.00000000","is_default":true,"name":"LINK Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"25fbcfdd-d49b-499c-836c-f57cd0067217"},
{"type":"wallet","attributes":{"cryptocoin_id":"26","cryptocoin_symbol":"WAVES","balance":"0.00000000","is_default":true,"name":"WAVEs Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"ec840687-3751-4ccd-a837-4cc008169317"},
{"type":"wallet","attributes":{"cryptocoin_id":"27","cryptocoin_symbol":"USDT","balance":"0.00000000","is_default":true,"name":"USDT Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"432e1f6a-01a5-4cff-b814-9225ed66f1b2"},
{"type":"wallet","attributes":{"cryptocoin_id":"30","cryptocoin_symbol":"USDC","balance":"0.00000000","is_default":true,"name":"USDC Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"f5326219-86c9-4ab3-ac6a-f5256b8834d1"},
{"type":"wallet","attributes":{"cryptocoin_id":"31","cryptocoin_symbol":"TRX","balance":"0.00000000","is_default":true,"name":"TRX Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"ef8827a8-9039-406e-8375-e7c4f8e70a8d"},
{"type":"wallet","attributes":{"cryptocoin_id":"32","cryptocoin_symbol":"ATOM","balance":"0.00000000","is_default":true,"name":"ATOM Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"544db22a-77ca-4481-a09b-dbdcf9e5592c"},
{"type":"wallet","attributes":{"cryptocoin_id":"33","cryptocoin_symbol":"BEST","balance":"210","is_default":true,"name":"BEST Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"83dc391a-1f88-412a-ad10-e684a61edfad"},
{"type":"wallet","attributes":{"cryptocoin_id":"34","cryptocoin_symbol":"BAT","balance":"0.00000000","is_default":true,"name":"BAT Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"c5c5560a-93bf-4ce3-8269-2424a5bef8e7"},
{"type":"wallet","attributes":{"cryptocoin_id":"37","cryptocoin_symbol":"CHZ","balance":"0.00000000","is_default":true,"name":"CHZ Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"211f91eb-525a-47e1-87c4-11589b130a6b"},
{"type":"wallet","attributes":{"cryptocoin_id":"38","cryptocoin_symbol":"DOGE","balance":"0.00000000","is_default":true,"name":"DOGE Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"c3ee1ed9-15ef-4fd0-add5-8f887ac6c892"},
{"type":"wallet","attributes":{"cryptocoin_id":"39","cryptocoin_symbol":"ONT","balance":"0.00000000","is_default":true,"name":"ONT Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"b97210a6-6d64-4a0b-98b0-a7fa215f7dba"},
{"type":"wallet","attributes":{"cryptocoin_id":"43","cryptocoin_symbol":"QTUM","balance":"0.00000000","is_default":true,"name":"QTUM Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"88dd935d-e6ae-45a1-9306-73d28d715043"},
{"type":"wallet","attributes":{"cryptocoin_id":"44","cryptocoin_symbol":"VET","balance":"0.00000000","is_default":true,"name":"VET Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"136a6470-18c5-4411-93c4-1d5d0bb1c6cd"},
{"type":"wallet","attributes":{"cryptocoin_id":"46","cryptocoin_symbol":"BNB","balance":"0.00000000","is_default":true,"name":"BNB Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"c779afab-467e-4a63-997d-9df4a5e4093e"},
{"type":"wallet","attributes":{"cryptocoin_id":"51","cryptocoin_symbol":"DOT","balance":"0.00000000","is_default":true,"name":"DOT Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"b638fbb5-6b8f-438c-96f5-84bed9dfb57b"},
{"type":"wallet","attributes":{"cryptocoin_id":"52","cryptocoin_symbol":"YFI","balance":"0.00000000","is_default":true,"name":"YFI Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"a7c46024-1508-4e47-91bd-11649cbac9dc"},
{"type":"wallet","attributes":{"cryptocoin_id":"53","cryptocoin_symbol":"MKR","balance":"0.00000000","is_default":true,"name":"MKR Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"15b9221c-aef1-412b-8ff8-995ad142bd24"},
{"type":"wallet","attributes":{"cryptocoin_id":"54","cryptocoin_symbol":"COMP","balance":"0.00000000","is_default":true,"name":"COMP Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"859224d6-bf55-4ebe-9b6b-fac40f7a1e22"},
{"type":"wallet","attributes":{"cryptocoin_id":"55","cryptocoin_symbol":"SNX","balance":"0.00000000","is_default":true,"name":"SNX Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"5109dd9b-a62b-4b40-b4b1-2f3370491561"},
{"type":"wallet","attributes":{"cryptocoin_id":"56","cryptocoin_symbol":"UNI","balance":"0.00000000","is_default":true,"name":"UNI Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"bcf4c118-a873-49fc-b41d-8569c2b94822"},
{"type":"wallet","attributes":{"cryptocoin_id":"57","cryptocoin_symbol":"FIL","balance":"0.00000000","is_default":true,"name":"FIL Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"c5b9ae1a-36fe-4a43-acc3-91d92687497d"},
{"type":"wallet","attributes":{"cryptocoin_id":"58","cryptocoin_symbol":"AAVE","balance":"0.00000000","is_default":true,"name":"AAVE Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"16fa51b4-26b1-4887-a065-2f32105fe7fb"},
{"type":"wallet","attributes":{"cryptocoin_id":"59","cryptocoin_symbol":"KNC","balance":"0.00000000","is_default":true,"name":"KNC Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"3cd79763-e550-4948-82d7-408e6de784d3"},
{"type":"wallet","attributes":{"cryptocoin_id":"60","cryptocoin_symbol":"BAND","balance":"0.00000000","is_default":true,"name":"BAND Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"ecee2c3c-8498-473f-b6f7-7252bb78307d"},
{"type":"wallet","attributes":{"cryptocoin_id":"61","cryptocoin_symbol":"REN","balance":"0.00000000","is_default":true,"name":"REN Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"62520e6f-7547-46b6-8e8a-b6d8fcf701e1"},
{"type":"wallet","attributes":{"cryptocoin_id":"63","cryptocoin_symbol":"UMA","balance":"0.00000000","is_default":true,"name":"UMA Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"db8f1984-1548-45d7-8352-d0c825505507"},
{"type":"wallet","attributes":{"cryptocoin_id":"65","cryptocoin_symbol":"THETA","balance":"0.00000000","is_default":true,"name":"THETA Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"3cca7945-e8cf-4320-b8a2-eabe74f27f5d"},
{"type":"wallet","attributes":{"cryptocoin_id":"66","cryptocoin_symbol":"OCEAN","balance":"0.00000000","is_default":true,"name":"OCEAN Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"72afcccf-ffd7-404b-9325-a4c25c61c727"},
{"type":"wallet","attributes":{"cryptocoin_id":"67","cryptocoin_symbol":"AVAX","balance":"0.00000000","is_default":true,"name":"AVAX Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"41d87f83-6db1-4aa0-b200-fc05327fbdb7"},
{"type":"wallet","attributes":{"cryptocoin_id":"68","cryptocoin_symbol":"ALGO","balance":"0.00000000","is_default":true,"name":"ALGO Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"497a1676-ebf7-4086-8bfe-c5718272da67"},
{"type":"wallet","attributes":{"cryptocoin_id":"69","cryptocoin_symbol":"ANT","balance":"0.00000000","is_default":true,"name":"ANT Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"39769ee1-49e1-454c-ba22-450b38648103"},
{"type":"wallet","attributes":{"cryptocoin_id":"70","cryptocoin_symbol":"BTT","balance":"0.00000000","is_default":true,"name":"BTT Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"0747da4f-2459-4456-96ed-1a9bbbb573ce"},
{"type":"wallet","attributes":{"cryptocoin_id":"71","cryptocoin_symbol":"DGB","balance":"0.00000000","is_default":true,"name":"DGB Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"806283ec-efed-4a21-b48f-17ed6657e0d4"},
{"type":"wallet","attributes":{"cryptocoin_id":"129","cryptocoin_symbol":"1INCH","balance":"0.00000000","is_default":true,"name":"1INCH Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"b7f03953-ec2c-4c6c-87a8-095e2fd4a2c8"},
{"type":"wallet","attributes":{"cryptocoin_id":"130","cryptocoin_symbol":"EGLD","balance":"0.00000000","is_default":true,"name":"EGLD Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"f3b18dbd-2be2-43ef-931e-34f523923eb0"},
{"type":"wallet","attributes":{"cryptocoin_id":"131","cryptocoin_symbol":"GRT","balance":"0.00000000","is_default":true,"name":"GRT Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"dddbdf34-4518-4877-a0a0-1445075a6fca"},
{"type":"wallet","attributes":{"cryptocoin_id":"132","cryptocoin_symbol":"IOST","balance":"0.00000000","is_default":true,"name":"IOST Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"ea6692e5-c453-4a46-949e-d0e6cc824dcb"},
{"type":"wallet","attributes":{"cryptocoin_id":"133","cryptocoin_symbol":"LUNA","balance":"0.00000000","is_default":true,"name":"LUNA Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"74cd087a-0727-4e8e-bd03-a3fbf66cf882"},
{"type":"wallet","attributes":{"cryptocoin_id":"134","cryptocoin_symbol":"MATIC","balance":"0.00000000","is_default":true,"name":"MATIC Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"6eb5624d-fd85-4b61-b255-110b6997fdb8"},
{"type":"wallet","attributes":{"cryptocoin_id":"135","cryptocoin_symbol":"SOL","balance":"0.00000000","is_default":true,"name":"SOL Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"84b6ed03-d8b6-4749-836e-e9b617b06b76"},
{"type":"wallet","attributes":{"cryptocoin_id":"136","cryptocoin_symbol":"ICP","balance":"0.00000000","is_default":true,"name":"ICP Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"eef09a7f-37fd-447b-aca8-42d517de9cdc"},
{"type":"wallet","attributes":{"cryptocoin_id":"138","cryptocoin_symbol":"MANA","balance":"0.00000000","is_default":true,"name":"MANA Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"e2c9c7de-989b-48ab-ac42-9ce06b1bf76c"},
{"type":"wallet","attributes":{"cryptocoin_id":"139","cryptocoin_symbol":"CAKE","balance":"0.00000000","is_default":true,"name":"CAKE Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"60e52ab8-adff-45e3-8ea8-fd879838546f"},
{"type":"wallet","attributes":{"cryptocoin_id":"140","cryptocoin_symbol":"KSM","balance":"0.00000000","is_default":true,"name":"KSM Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"3a8e27ed-ea15-417b-8de9-a56e6d8f290d"},
{"type":"wallet","attributes":{"cryptocoin_id":"141","cryptocoin_symbol":"SUSHI","balance":"0.00000000","is_default":true,"name":"SUSHI Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"d884f0fa-8670-433a-bc1f-5bdced2f29cb"},
{"type":"wallet","attributes":{"cryptocoin_id":"142","cryptocoin_symbol":"KLAY","balance":"0.00000000","is_default":true,"name":"KLAY Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"9555ebdd-84bc-4e9a-bb84-a12bd85c28cd"},
{"type":"wallet","attributes":{"cryptocoin_id":"143","cryptocoin_symbol":"XYM","balance":"0.00000000","is_default":true,"name":"XYM Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"660aed65-0fc4-4e52-b919-f0411d8b932e"},
{"type":"wallet","attributes":{"cryptocoin_id":"151","cryptocoin_symbol":"AXS","balance":"15.50000000","is_default":true,"name":"AXS Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"3d69c0d6-d062-48b7-88c6-d1e050ea6da6"},
        {"type":"wallet","attributes":{"cryptocoin_id":"193","cryptocoin_symbol":"SHIB","balance":"0.00000000","is_default":true,"name":"SHIB Wallet","pending_transactions_count":0,"deleted":false,"is_index":false},"id":"55edb379-1a03-4ad9-a031-944327aa19e6"}]}"""  # noqa: E501

FIAT_WALLETS_RESPONSE = """{"data":[{"type":"fiat_wallet","attributes":{"fiat_id":"3","fiat_symbol":"CHF","balance":"0.00","name":"CHF Wallet","pending_transactions_count":0},"id":"d8a96548-ceed-4848-9b9e-89fe88a64a44"},{"type":"fiat_wallet","attributes":{"fiat_id":"1","fiat_symbol":"EUR","balance":"1500.51","name":"EUR Wallet","pending_transactions_count":0},"id":"7161d200-3f59-4c4f-ab8e-53378317740c"},{"type":"fiat_wallet","attributes":{"fiat_id":"4","fiat_symbol":"GBP","balance":"0.00","name":"GBP Wallet","pending_transactions_count":0},"id":"07dcb81e-74bd-4b43-8812-59edbdc792a8"},{"type":"fiat_wallet","attributes":{"fiat_id":"8","fiat_symbol":"TRY","balance":"155.22","name":"TRY Wallet","pending_transactions_count":0},"id":"e1526b07-ced7-43a4-a692-aa2e07ee71df"},{"type":"fiat_wallet","attributes":{"fiat_id":"2","fiat_symbol":"USD","balance":"0.00","name":"USD Wallet","pending_transactions_count":0},"id":"0e7d9a1b-4639-48c3-93fc-85156a130ee1"}]}"""  # noqa: E501


@pytest.mark.parametrize('mocked_current_prices', [{
    A_BEST: FVal(20),
    A_ETH: FVal(3000),
    A_AXS: FVal(40),
    A_EUR: FVal(0.85),
    A_TRY: FVal(0.103),
}])
def test_balances(mock_bitpanda):
    """Test that balances are correctly queried"""

    def mock_bitpanda_query(url: str, **kwargs):  # pylint: disable=unused-argument
        if '/wallets' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=WALLETS_RESPONSE)
        if '/fiatwallets' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=FIAT_WALLETS_RESPONSE)
        # else
        raise AssertionError(f'Unexpected url {url} in bitpanda test')

    with patch.object(mock_bitpanda.session, 'get', side_effect=mock_bitpanda_query):
        balances, msg = mock_bitpanda.query_balances()

    warnings = mock_bitpanda.msg_aggregator.consume_warnings()
    errors = mock_bitpanda.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0

    assert msg == ''
    assert len(balances) == 5
    assert balances[A_ETH].amount == FVal('100.55')
    assert balances[A_ETH].usd_value == FVal('301650')
    assert balances[A_BEST].amount == FVal('210')
    assert balances[A_BEST].usd_value == FVal('4200')
    assert balances[A_AXS].amount == FVal('15.5')
    assert balances[A_AXS].usd_value == FVal('620')
    assert balances[A_EUR].amount == FVal('1500.51')
    assert balances[A_EUR].usd_value == FVal('1275.4335')
    assert balances[A_TRY].amount == FVal('155.22')
    assert balances[A_TRY].usd_value == FVal('15.98766')


TRADES_RESPONSE = """{"data":[
{"type":"trade","attributes":{"status":"finished","type":"buy","cryptocoin_id":"3","fiat_id":"1","amount_fiat":"1.63","amount_cryptocoin":"0.00917887","fiat_to_eur_rate":"1.00000000","wallet_id":"foo","fiat_wallet_id":"foo","payment_option_id":"12","time":{"date_iso8601":"2021-10-23T05:30:18+01:00","unix":"1634963958"},"price":"180.85","is_swap":false,"is_savings":false,"tags":[],"bfc_used":true,"best_fee_collection":{"type":"best_fee_collection","attributes":{"best_current_price_eur":"0.96623970","best_used_price_eur":"0.96623970","bfc_deduction":0.2001,"bfc_market_value_eur":"0.03000000","wallet_transaction":{"type":"wallet_transaction","attributes":{"amount":"0.00000000","recipient":"Bitpanda","time":{"date_iso8601":"2021-10-23T05:30:18+01:00","unix":"1634963958"},"confirmations":99,"in_or_out":"outgoing","type":"withdrawal","status":"finished","amount_eur":"0.00","wallet_id":"foo","confirmation_by":"not_required","confirmed":false,"cryptocoin_id":"33","cryptocoin_symbol":"BEST","last_changed":{"date_iso8601":"2021-10-23T05:30:18+01:00","unix":"1634963958"},"fee":"1.71800028","current_fiat_id":"1","current_fiat_amount":"0.00","is_metal_storage_fee":false,"tags":[],"public_status":"finished","is_bfc":true,"is_card":false}}}},"is_card":false},"id":"tradeid1"},
{"type":"trade","attributes":{"status":"finished","type":"sell","cryptocoin_id":"22","fiat_id":"1","amount_fiat":"12.93","amount_cryptocoin":"5.37267451","fiat_to_eur_rate":"1.00000000","wallet_id":"foo","fiat_wallet_id":"foo","payment_option_id":"12","time":{"date_iso8601":"2021-08-20T08:26:07+02:00","unix":"1629440767"},"price":"2.4079","is_swap":false,"is_savings":false,"tags":[],"bfc_used":false,"is_card":false},"id":"tradeid2"}],
"meta":{"total_count":2,"page":1,"page_size":100},"links":{"self":"?page=1&page_size=100"}}
"""
EMPTY_RESPONSE: Final = '{"data":[],"meta":{"total_count":0}}'


def test_trades(mock_bitpanda):
    """Test that trades are correctly queried"""

    def mock_bitpanda_query(url: str, **kwargs):  # pylint: disable=unused-argument
        if '/wallets/transactions' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=EMPTY_RESPONSE)
        if '/wallets' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=WALLETS_RESPONSE)
        if '/fiatwallets/transactions' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=EMPTY_RESPONSE)
        if '/fiatwallets' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=FIAT_WALLETS_RESPONSE)
        if '/trades' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=TRADES_RESPONSE)

        # else
        raise AssertionError(f'Unexpected url {url} in bitpanda test')

    with patch.object(mock_bitpanda.session, 'get', side_effect=mock_bitpanda_query):
        events, _ = mock_bitpanda.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )

    warnings = mock_bitpanda.msg_aggregator.consume_warnings()
    errors = mock_bitpanda.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0

    assert events == [SwapEvent(
        timestamp=TimestampMS(1634963958000),
        location=Location.BITPANDA,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        amount=FVal('1.6599986395'),
        location_label='bitpanda',
        unique_id='tradeid1',
    ),
    SwapEvent(
        timestamp=TimestampMS(1634963958000),
        location=Location.BITPANDA,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_LTC,
        amount=FVal('0.00917887'),
        location_label='bitpanda',
        unique_id='tradeid1',
    ),
    SwapEvent(
        timestamp=TimestampMS(1634963958000),
        location=Location.BITPANDA,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BEST,
        amount=FVal('1.71800028'),
        location_label='bitpanda',
        unique_id='tradeid1',
    ),
    SwapEvent(
        timestamp=TimestampMS(1629440767000),
        location=Location.BITPANDA,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ADA,
        amount=FVal('5.37267451'),
        location_label='bitpanda',
        unique_id='tradeid2',
    ),
    SwapEvent(
        timestamp=TimestampMS(1629440767000),
        location=Location.BITPANDA,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_EUR,
        amount=FVal('12.936862952629'),
        location_label='bitpanda',
        unique_id='tradeid2',
    )]


FIATWALLETS_TX_RESPONSE = """{"data":[
{"type":"fiat_wallet_transaction","attributes":{"fiat_wallet_id":"foo","user_id":"foo","fiat_id":"1","amount":"25.00","fee":"0.00","to_eur_rate":"1.00000000","time":{"date_iso8601":"2021-09-08T09:09:28+01:00","unix":"1631088548"},"in_or_out":"incoming","type":"deposit","status":"finished","confirmation_by":"not_required","confirmed":true,"payment_option_id":"5","requires_2fa_approval":false,"is_savings":true,"last_changed":{"date_iso8601":"2021-09-08T09:09:28+01:00","unix":"1631088548"},"tags":[{"type":"tag","attributes":{"short_name":"savings.reserved_for_trade","name":"F\\u00fcr den Trade reserviert"}}],"public_status":"finished","bank_account_details":{"type":"bank_account_detail","attributes":{"country_id":"XX","iban":"XXX","bic":"XX","bank_name":"XX","holder":"XX"}},"is_index":false,"is_card":false,"is_card_order_charge":false},"id":"movementid1"},
{"type":"fiat_wallet_transaction","attributes":{"fiat_wallet_id":"foo","user_id":"foo","fiat_id":"1","amount":"50.00","fee":"0.01","to_eur_rate":"1.00000000","time":{"date_iso8601":"2021-09-17T15:22:28+01:00","unix":"1631888548"},"in_or_out":"outgoing","type":"withdrawal","status":"finished","confirmation_by":"not_required","confirmed":true,"payment_option_id":"5","requires_2fa_approval":false,"is_savings":true,"last_changed":{"date_iso8601":"2021-09-17T15:22:28+01:00","unix":"1631888548"},"tags":[{"type":"tag","attributes":{"short_name":"savings.reserved_for_trade","name":"F\\u00fcr den Trade reserviert"}}],"public_status":"finished","is_index":false,"is_card":false,"is_card_order_charge":false},"id":"movementid2"}],
"meta":{"total_count":2,"page":1,"page_size":100},"links":{"self":"?page=1&page_size=100"}}"""  # noqa: E501

WALLET_TX_RESPONSE = """{"data":[{"type":"wallet_transaction","attributes":{"amount":"6608.34105600","recipient":"0x54dca71a34f498e3053cba240895e51da5f89d24","time":{"date_iso8601":"2021-10-10T09:01:12+02:00","unix":"1633849272"},"confirmations":56,"in_or_out":"incoming","type":"deposit","status":"finished","amount_eur":"5718.43","amount_eur_incl_fee":"5718.43","wallet_id":"XXX","confirmation_by":"not_required","confirmed":false,"cryptocoin_id":"27","cryptocoin_symbol":"USDT","last_changed":{"date_iso8601":"2021-10-10T09:15:45+02:00","unix":"1633850145"},"fee":"0.00000000","current_fiat_id":"1","current_fiat_amount":"5718.43","tx_id":"0x28cb2ba8ac14bdedb0ad021662b631952ce2514f1e3ff7870882ebe8a8c1b03f","is_metal_storage_fee":false,"tags":[],"public_status":"finished","is_bfc":false,"is_card":false},"id":"XXX"},{"type":"wallet_transaction","attributes":{"amount":"1.55165264","recipient":"0x54dca71a34f498e3053cba240895e51da5f89d24","time":{"date_iso8601":"2020-08-10T17:10:46+02:00","unix":"1597072246"},"confirmations":8,"in_or_out":"outgoing","type":"withdrawal","status":"finished","amount_eur":"524.09","amount_eur_incl_fee":"526.66","purpose_text":"","wallet_id":"XXX","contact_id":"XXX","confirmation_by":"email","confirmed":true,"cryptocoin_id":"5","cryptocoin_symbol":"ETH","last_changed":{"date_iso8601":"2020-08-10T17:12:24+02:00","unix":"1597072344"},"fee":"0.00762000","current_fiat_id":"1","current_fiat_amount":"524.09","tx_id":"0xe45c1befc0968d2dab0374bc8d1aa3e193136dc769596d42e4d3274475bc7c60","is_metal_storage_fee":false,"tags":[],"public_status":"finished","is_bfc":false,"is_card":false},"id":"XXX"}],
"meta":{"total_count":2,"page":1,"page_size":10},"links":{"next":"?page=2&page_size=10","last":"?page=20&page_size=10","self":"?page=1&page_size=10"}}"""  # noqa: E501


def test_asset_movements(database, mock_bitpanda):
    """Test that deposits/withdrawals are correctly queried"""

    def mock_bitpanda_query(url: str, **kwargs):  # pylint: disable=unused-argument
        if '/wallets/transactions' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=WALLET_TX_RESPONSE)
        if '/wallets' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=WALLETS_RESPONSE)
        if '/fiatwallets/transactions' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=FIATWALLETS_TX_RESPONSE)
        if '/fiatwallets' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=FIAT_WALLETS_RESPONSE)
        if '/trades' in url:
            return MockResponse(status_code=HTTPStatus.OK, text=EMPTY_RESPONSE)

        # else
        raise AssertionError(f'Unexpected url {url} in bitpanda test')

    with patch.object(mock_bitpanda.session, 'get', side_effect=mock_bitpanda_query):
        mock_bitpanda.query_history_events()

    with database.conn.read_ctx() as cursor:
        movements = DBHistoryEvents(database).get_history_events(
            cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.BITPANDA),
            has_premium=True,
        )

    warnings = mock_bitpanda.msg_aggregator.consume_warnings()
    errors = mock_bitpanda.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0

    expected_movements = [AssetMovement(
        identifier=5,
        event_identifier='bc9ae2697f378ed91ce77120c3a29e635c435ecb752865760e5e9304aed35759',
        location=Location.BITPANDA,
        location_label=mock_bitpanda.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1597072246000),
        asset=A_ETH,
        amount=FVal('1.55165264'),
        extra_data={
            'address': '0x54dca71a34f498e3053cba240895e51da5f89d24',
            'transaction_id': '0xe45c1befc0968d2dab0374bc8d1aa3e193136dc769596d42e4d3274475bc7c60',
        },
    ), AssetMovement(
        identifier=6,
        event_identifier='bc9ae2697f378ed91ce77120c3a29e635c435ecb752865760e5e9304aed35759',
        location=Location.BITPANDA,
        location_label=mock_bitpanda.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1597072246000),
        asset=A_ETH,
        amount=FVal('0.00762000'),
        is_fee=True,
    ), AssetMovement(
        identifier=1,
        event_identifier='417fa4b6bcb5ff3b9050d84ddff00e3e423333512bca8f36a430bccf72634c20',
        location=Location.BITPANDA,
        location_label=mock_bitpanda.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1631088548000),
        asset=A_EUR,
        amount=FVal('25.00'),
    ), AssetMovement(
        identifier=2,
        event_identifier='7db139d1cf52facb8f9043e2fe73e924c3b58d54b27f38574d9a73e74a1c5bd1',
        location=Location.BITPANDA,
        location_label=mock_bitpanda.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1631888548000),
        asset=A_EUR,
        amount=FVal('50.00'),
    ), AssetMovement(
        identifier=3,
        event_identifier='7db139d1cf52facb8f9043e2fe73e924c3b58d54b27f38574d9a73e74a1c5bd1',
        location=Location.BITPANDA,
        location_label=mock_bitpanda.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1631888548000),
        asset=A_EUR,
        amount=FVal('0.01'),
        is_fee=True,
    ), AssetMovement(
        identifier=4,
        event_identifier='eedabacb4b72276581975459254fcb3d603dc46900335d40055adcc32cbd69ed',
        location=Location.BITPANDA,
        location_label=mock_bitpanda.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1633849272000),
        asset=A_USDT,
        amount=FVal('6608.34105600'),
        extra_data={
            'address': '0x54dca71a34f498e3053cba240895e51da5f89d24',
            'transaction_id': '0x28cb2ba8ac14bdedb0ad021662b631952ce2514f1e3ff7870882ebe8a8c1b03f',
        },
    )]
    assert expected_movements == movements
