from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import call, patch

from solders.solders import Signature

from rotkehlchen.db.filtering import SolanaTransactionsFilterQuery
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.externalapis.helius import HELIUS_API_URL, Helius
from rotkehlchen.tests.utils.factories import make_solana_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ApiKey, ExternalService, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

JUPITER_SWAP_TX_RESPONSE: Final = '[{"description":"","type":"UNKNOWN","source":"UNKNOWN","fee":10195,"feePayer":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","signature":"5vBFfTGrcdkE7ZdsUDSU2kRkhoFp4EgKtLLB6h2m1uQoG5wCddCkFGnNjXaHrV2r1kZ8CpJfh7UcWJ9tFXAyKc8Q","slot":367689024,"timestamp":1758217531,"tokenTransfers":[{"fromTokenAccount":"DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","toTokenAccount":"HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","fromUserAccount":"7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","toUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","tokenAmount":0.00287442,"mint":"7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs","tokenStandard":"Fungible"},{"fromTokenAccount":"BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","toTokenAccount":"ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","fromUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","toUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","tokenAmount":0.052708178,"mint":"So11111111111111111111111111111111111111112","tokenStandard":"Fungible"}],"nativeTransfers":[{"fromUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","toUserAccount":"ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","amount":2039280},{"fromUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","toUserAccount":"7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","amount":52708178},{"fromUserAccount":"ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","toUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","amount":54747458}],"accountData":[{"account":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","nativeBalanceChange":-10195,"tokenBalanceChanges":[]},{"account":"7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","nativeBalanceChange":52708178,"tokenBalanceChanges":[]},{"account":"DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","nativeBalanceChange":0,"tokenBalanceChanges":[{"userAccount":"7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","tokenAccount":"DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","rawTokenAmount":{"tokenAmount":"-287442","decimals":8},"mint":"7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"}]},{"account":"ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","nativeBalanceChange":-52708178,"tokenBalanceChanges":[{"userAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","tokenAccount":"BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","rawTokenAmount":{"tokenAmount":"-52708178","decimals":9},"mint":"So11111111111111111111111111111111111111112"}]},{"account":"HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","nativeBalanceChange":0,"tokenBalanceChanges":[{"userAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","tokenAccount":"HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","rawTokenAmount":{"tokenAmount":"287442","decimals":8},"mint":"7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"}]},{"account":"11111111111111111111111111111111","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"ComputeBudget111111111111111111111111111111","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"So11111111111111111111111111111111111111112","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"61DFfeTKM7trxYcPQCM78bJ794ddZprZpAwAnLiwTpYH","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs","nativeBalanceChange":0,"tokenBalanceChanges":[]}],"transactionError":null,"instructions":[{"accounts":[],"data":"3Ddz2qHp11eo","programId":"ComputeBudget111111111111111111111111111111","innerInstructions":[]},{"accounts":[],"data":"FV2PdR","programId":"ComputeBudget111111111111111111111111111111","innerInstructions":[]},{"accounts":["7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","61DFfeTKM7trxYcPQCM78bJ794ddZprZpAwAnLiwTpYH","BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs","TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","So11111111111111111111111111111111111111112","TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","11111111111111111111111111111111","ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj"],"data":"HoSdaJgwWtUbjM99F3S6JbDjpMBo54SfrpbRD2guKECL96pP","programId":"61DFfeTKM7trxYcPQCM78bJ794ddZprZpAwAnLiwTpYH","innerInstructions":[{"accounts":["DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY"],"data":"3peYHhHYfToD","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj"],"data":"11119os1e9qSs2u7TsThXqkBSRVFxhmYaFKFZ1waB2X7armDmvK3p5GmLdUxYdg3h7QSrL","programId":"11111111111111111111111111111111"},{"accounts":["ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","So11111111111111111111111111111111111111112"],"data":"6TzQdiY1vUxPdN7EL5BHWAHaLdefTocuM8W7bLWVYttDN","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ"],"data":"3TDcKxZ3zT7u","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ"],"data":"A","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY"],"data":"3Bxs4EchykAmQrVD","programId":"11111111111111111111111111111111"}]}],"events":{}}]'  # noqa: E501


def test_get_transactions(database: 'DBHandler'):
    """Test that querying transactions from the Helius API works correctly.
    Simulates batched requests and checks that a tx is deserialized properly
    from the mocked api response.
    """
    swap_tx_signature = '5vBFfTGrcdkE7ZdsUDSU2kRkhoFp4EgKtLLB6h2m1uQoG5wCddCkFGnNjXaHrV2r1kZ8CpJfh7UcWJ9tFXAyKc8Q'  # noqa: E501
    # Add a fake api key so it doesn't do a missing api key error (all requests are mocked).
    with database.user_write() as write_cursor:
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.HELIUS,
                api_key=ApiKey('xyz'),
            )])

    def mock_post(url: str, json: dict[str, Any], **kwargs: Any) -> MockResponse:
        """Mock the Helius API post request."""
        if 'transactions' in json and swap_tx_signature in json['transactions']:
            response_text = JUPITER_SWAP_TX_RESPONSE
        else:
            response_text = '[]'

        return MockResponse(status_code=HTTPStatus.OK, text=response_text)

    with (
        patch('rotkehlchen.externalapis.helius.requests.post', side_effect=mock_post) as post_mock,
        patch('rotkehlchen.externalapis.helius.MAX_TX_BATCH_SIZE', new=2),  # Force pagination
    ):
        Helius(database=database).get_transactions(
            signatures=[
                swap_tx_signature,
                (other_tx_sig_1 := '4PXgKteR5ofZLbMGxNzstUc5f1GHLVoPh47FCaXLRETARUtym99DtW74EmxjazpQ94BJeMAPiYXEjiBGDeioj32y'),  # noqa: E501
                (other_tx_sig_2 := '5LB5yWMEqGZLTQxuSmU3un4dVZoCZbXBrQJnW2zXJhZu2WaYfdtUKpzwGPZk8AdRPQ9yqfFN5HetrgpDP6DWXx5a'),  # noqa: E501
            ],
            relevant_address=make_solana_address(),
        )

    # Check that requests are properly batched
    assert post_mock.call_args_list == [call(
        url=f'{HELIUS_API_URL}/transactions/?api-key=xyz',
        json={'transactions': [swap_tx_signature, other_tx_sig_1]},
        timeout=(timeout := CachedSettings().get_timeout_tuple()),
    ), call(
        url=f'{HELIUS_API_URL}/transactions/?api-key=xyz',
        json={'transactions': [other_tx_sig_2]},
        timeout=timeout,
    )]

    with database.conn.read_ctx() as cursor:
        txs = DBSolanaTx(database).get_solana_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(),
        )

    assert len(txs) == 1  # the mocked response only includes tx data for the jupiter swap tx
    tx = txs[0]  # Check some properties of the deserialized transaction
    assert tx.signature == Signature.from_string(swap_tx_signature)
    assert tx.fee == 10195
    assert tx.slot == 367689024
    assert tx.block_time == 1758217531
    assert tx.success is True
    assert len(tx.account_keys) == 12
    assert len(tx.instructions) == 9
    assert len([x for x in tx.instructions if x.parent_execution_index == 2]) == 6
    assert len([x for x in tx.instructions if x.parent_execution_index is None]) == 3
