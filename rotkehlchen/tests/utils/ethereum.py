import logging
import os
from typing import TYPE_CHECKING, Any, overload
from unittest.mock import patch

import gevent
from eth_typing import ChecksumAddress

from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
from rotkehlchen.chain.arbitrum_one.transactions import ArbitrumOneTransactions
from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
from rotkehlchen.chain.base.transactions import BaseTransactions
from rotkehlchen.chain.binance_sc.decoding.decoder import BinanceSCTransactionDecoder
from rotkehlchen.chain.binance_sc.transactions import BinanceSCTransactions
from rotkehlchen.chain.ethereum.constants import (
    ETHEREUM_ETHERSCAN_NODE,
    ETHEREUM_ETHERSCAN_NODE_NAME,
)
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.chain.gnosis.decoding.decoder import GnosisTransactionDecoder
from rotkehlchen.chain.gnosis.transactions import GnosisTransactions
from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
from rotkehlchen.chain.optimism.transactions import OptimismTransactions
from rotkehlchen.chain.polygon_pos.decoding.decoder import PolygonPOSTransactionDecoder
from rotkehlchen.chain.polygon_pos.transactions import PolygonPOSTransactions
from rotkehlchen.chain.scroll.decoding.decoder import ScrollTransactionDecoder
from rotkehlchen.chain.scroll.transactions import ScrollTransactions
from rotkehlchen.constants import ONE
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

NODE_CONNECTION_TIMEOUT = 10

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

INFURA_TEST = 'https://mainnet.infura.io/v3/a6b269b6e5ad44ed943e9fff244dfe25'
ALCHEMY_TEST = 'https://eth-mainnet.alchemyapi.io/v2/ga1GtB7R26UgzjextaVpbaWZ49nSi2zt'

PRUNED_AND_NOT_ARCHIVED_NODE = WeightedNode(
    node_info=NodeName(
        name='Public Node',
        endpoint='https://ethereum.publicnode.com',
        owned=True,
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
    active=True,
    weight=ONE,
)
ANKR_NODE = WeightedNode(
    node_info=NodeName(
        name='own',
        endpoint='https://rpc.ankr.com/eth',
        owned=True,
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
    weight=ONE,
    active=True,
)

ETHERSCAN_AND_INFURA_PARAMS: tuple[str, list[tuple]] = ('ethereum_manager_connect_at_start, call_order', [  # noqa: E501
    ((), (ETHEREUM_ETHERSCAN_NODE,)),
    (
        (WeightedNode(node_info=NodeName(name='own', endpoint=INFURA_TEST, owned=True, blockchain=SupportedBlockchain.ETHEREUM), weight=ONE, active=True),),  # noqa: E501
        (WeightedNode(node_info=NodeName(name='own', endpoint=INFURA_TEST, owned=True, blockchain=SupportedBlockchain.ETHEREUM), weight=ONE, active=True),),  # noqa: E501
    ),
])


ETHERSCAN_AND_INFURA_AND_ALCHEMY: tuple[str, list[tuple]] = ('ethereum_manager_connect_at_start, call_order', [  # noqa: E501
    # Query etherscan only
    ((), (ETHEREUM_ETHERSCAN_NODE,)),
    # For "our own" node querying use infura
    (
        (WeightedNode(node_info=NodeName(name='own', endpoint=INFURA_TEST, owned=True, blockchain=SupportedBlockchain.ETHEREUM), weight=ONE, active=True),),  # noqa: E501
        (WeightedNode(node_info=NodeName(name='own', endpoint=INFURA_TEST, owned=True, blockchain=SupportedBlockchain.ETHEREUM), weight=ONE, active=True),),  # noqa: E501
    ),
    (
        (WeightedNode(node_info=NodeName(name='own', endpoint=ALCHEMY_TEST, owned=True, blockchain=SupportedBlockchain.ETHEREUM), weight=ONE, active=True),),  # noqa: E501
        (WeightedNode(node_info=NodeName(name='own', endpoint=ALCHEMY_TEST, owned=True, blockchain=SupportedBlockchain.ETHEREUM), weight=ONE, active=True),),  # noqa: E501
    ),
])
TEST_ADDR1 = string_to_evm_address('0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea')
TEST_ADDR2 = string_to_evm_address('0x442068F934BE670aDAb81242C87144a851d56d16')

INFURA_ETH_NODE = WeightedNode(
    node_info=NodeName(
        name='Infura',
        endpoint='https://mainnet.infura.io/v3/a6b269b6e5ad44ed943e9fff244dfe25',
        owned=True,
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
    active=True,
    weight=ONE,
)


ETHEREUM_WEB3_AND_ETHERSCAN_TEST_PARAMETERS = (
    'ethereum_manager_connect_at_start',
    [
        (INFURA_ETH_NODE,),
        (ETHEREUM_ETHERSCAN_NODE,),
    ],
)


ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED = (
    'ethereum_manager_connect_at_start',
    [
        (PRUNED_AND_NOT_ARCHIVED_NODE,),
        (INFURA_ETH_NODE,),
        (ETHEREUM_ETHERSCAN_NODE,),
        (ETHERSCAN_AND_INFURA_AND_ALCHEMY[1][2][0][0],),
    ],
)

ETHEREUM_NODES_SET_WITH_PRUNED_AND_NOT_ARCHIVED = (
    'ethereum_manager_connect_at_start',
    [(
        PRUNED_AND_NOT_ARCHIVED_NODE,
        INFURA_ETH_NODE,
        ETHEREUM_ETHERSCAN_NODE,
        ETHERSCAN_AND_INFURA_AND_ALCHEMY[1][2][0][0],
    )],
)

# Test with etherscan and infura
ETHEREUM_TEST_PARAMETERS: tuple[str, list[tuple]]
if 'GITHUB_WORKFLOW' in os.environ:  # TODO: Undo this if once all tests where it's used are mockable  # noqa: E501
    # For Github actions don't use infura. It seems that connecting to it
    # from Github actions hangs and times out
    ETHEREUM_TEST_PARAMETERS = ('ethereum_manager_connect_at_start, call_order', [
        # Query etherscan only
        ((), (ETHEREUM_ETHERSCAN_NODE,)),
    ])
else:
    # For Travis and local tests also use Infura, works fine
    ETHEREUM_TEST_PARAMETERS = ETHERSCAN_AND_INFURA_PARAMS


def wait_until_all_nodes_connected(
        connect_at_start,
        evm_inquirer,
        timeout: int = NODE_CONNECTION_TIMEOUT,
):
    """Wait until all ethereum nodes are connected or until a timeout is hit"""
    connect_at_start = [x for x in connect_at_start if x.node_info.name != ETHEREUM_ETHERSCAN_NODE_NAME]  # noqa: E501
    connected = [False] * len(connect_at_start)
    try:
        with gevent.Timeout(timeout):
            while not all(connected):
                for idx, weighted_node in enumerate(connect_at_start):
                    if weighted_node.node_info in evm_inquirer.web3_mapping:
                        connected[idx] = True

                gevent.sleep(0.1)
    except gevent.Timeout:
        names = [
            str(x) for idx, x in enumerate(connect_at_start) if not connected[idx]
        ]
        log.warning(
            f'Did not connect to nodes: {",".join(names)} due to '
            f'timeout of {NODE_CONNECTION_TIMEOUT}. Connected to {connected}',
        )


def txreceipt_to_data(receipt: EvmTxReceipt) -> dict[str, Any]:
    """Turns it to receipt data as would be returned by web3

    Is here since this would only be done in test. In actual
    serialization snake case would be used.
    """
    data: dict[str, Any] = {
        'transactionHash': receipt.tx_hash.hex(),
        'type': hex(receipt.tx_type),
        'contractAddress': receipt.contract_address,
        'status': int(receipt.status),
        'logs': [],
    }
    for log_entry in receipt.logs:
        log_data = {
            'logIndex': log_entry.log_index,
            'address': log_entry.address,
            'data': '0x' + log_entry.data.hex(),
            'topics': [],
        }
        log_data['topics'] = ['0x' + topic.hex() for topic in log_entry.topics]
        data['logs'].append(log_data)

    return data


def setup_ethereum_transactions_test(
        database: DBHandler,
        transaction_already_queried: bool,
        one_receipt_in_db: bool = False,
        second_receipt_in_db: bool = False,
) -> tuple[list[EvmTransaction], list[EvmTxReceipt]]:
    """This setup assumes that TEST_ADDR1 and TEST_ADDR2 are already present in the db"""
    dbevmtx = DBEvmTx(database)
    tx_hash1 = deserialize_evm_tx_hash('0x692f9a6083e905bdeca4f0293f3473d7a287260547f8cbccc38c5cb01591fcda')  # noqa: E501
    transaction1 = EvmTransaction(
        tx_hash=tx_hash1,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1630532276),
        block_number=13142218,
        from_address=TEST_ADDR1,
        to_address=string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        value=10 * 10**18,
        gas=194928,
        gas_price=int(0.000000204 * 10**18),
        gas_used=136675,
        input_data=hexstring_to_bytes('0x7ff36ab5000000000000000000000000000000000000000000000367469995d0723279510000000000000000000000000000000000000000000000000000000000000080000000000000000000000000443e1f9b1c866e54e914822b7d3d7165edb6e9ea00000000000000000000000000000000000000000000000000000000612ff9b50000000000000000000000000000000000000000000000000000000000000002000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000002a3bff78b79a009976eea096a51a948a3dc00e34'),
        nonce=13,
    )
    tx_hash2 = deserialize_evm_tx_hash('0x6beab9409a8f3bd11f82081e99e856466a7daf5f04cca173192f79e78ed53a77')  # noqa: E501
    transaction2 = EvmTransaction(
        tx_hash=tx_hash2,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1631013757),
        block_number=13178342,
        from_address=TEST_ADDR2,
        to_address=string_to_evm_address('0xEaDD9B69F96140283F9fF75DA5FD33bcF54E6296'),
        value=0,
        gas=77373,
        gas_price=int(0.000000100314697497 * 10**18),
        gas_used=46782,
        input_data=hexstring_to_bytes('0xa9059cbb00000000000000000000000020c8032d4f7d4a380385f87aeadf05bed84504cb000000000000000000000000000000000000000000000000000000003b9deec6'),
        nonce=3,
    )
    transactions = [transaction1, transaction2]
    if transaction_already_queried is True:
        with database.user_write() as cursor:
            dbevmtx.add_evm_transactions(cursor, evm_transactions=[transaction1], relevant_address=TEST_ADDR1)  # noqa: E501
            dbevmtx.add_evm_transactions(cursor, evm_transactions=[transaction2], relevant_address=TEST_ADDR2)  # noqa: E501
            result = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(chain_id=ChainID.ETHEREUM), True)  # noqa: E501
        assert result == transactions

    expected_receipt1 = EvmTxReceipt(
        tx_hash=tx_hash1,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=295,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000008ac7230489e80000'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'),
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),
                ],
            ), EvmTxReceiptLog(
                log_index=296,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000008ac7230489e80000'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),
                    hexstring_to_bytes('0x000000000000000000000000caa004418eb42cdf00cb057b7c9e28f0ffd840a5'),
                ],
            ), EvmTxReceiptLog(
                log_index=297,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000036ba1d53baeeda5ed20'),
                address=string_to_evm_address('0x2a3bFF78B79A009976EeA096a51A948a3dC00e34'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000caa004418eb42cdf00cb057b7c9e28f0ffd840a5'),
                    hexstring_to_bytes('0x000000000000000000000000443e1f9b1c866e54e914822b7d3d7165edb6e9ea'),
                ],
            ), EvmTxReceiptLog(
                log_index=298,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000007b6ea033189ba7d047e30000000000000000000000000000000000000000000000140bc8194dd0f5e4be'),
                address=string_to_evm_address('0xcaA004418eB42cdf00cB057b7C9E28f0FfD840a5'),
                topics=[hexstring_to_bytes('0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1')],
            ), EvmTxReceiptLog(
                log_index=299,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008ac7230489e8000000000000000000000000000000000000000000000000036ba1d53baeeda5ed200000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0xcaA004418eB42cdf00cB057b7C9E28f0FfD840a5'),
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),
                    hexstring_to_bytes('0x000000000000000000000000443e1f9b1c866e54e914822b7d3d7165edb6e9ea'),
                ],
            ),
        ],
    )
    expected_receipt2 = EvmTxReceipt(
        tx_hash=tx_hash2,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=2,
        logs=[
            EvmTxReceiptLog(
                log_index=438,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000003b9deec6'),
                address=string_to_evm_address('0xEaDD9B69F96140283F9fF75DA5FD33bcF54E6296'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000442068f934be670adab81242c87144a851d56d16'),
                    hexstring_to_bytes('0x00000000000000000000000020c8032d4f7d4a380385f87aeadf05bed84504cb'),
                ],
            ),
        ],
    )

    if one_receipt_in_db is True:
        with database.user_write() as cursor:
            dbevmtx.add_or_ignore_receipt_data(cursor, ChainID.ETHEREUM, txreceipt_to_data(expected_receipt1))  # noqa: E501
            if second_receipt_in_db is True:
                dbevmtx.add_or_ignore_receipt_data(cursor, ChainID.ETHEREUM, txreceipt_to_data(expected_receipt2))  # noqa: E501

    return transactions, [expected_receipt1, expected_receipt2]


@overload
def get_decoded_events_of_transaction(
        evm_inquirer: 'EthereumInquirer',
        tx_hash: EVMTxHash,
        transactions: EvmTransactions | None = None,
        relevant_address: ChecksumAddress | None = None,
        load_global_caches: list[str] | None = None,
) -> tuple[list['EvmEvent'], EthereumTransactionDecoder]:
    ...


@overload
def get_decoded_events_of_transaction(
        evm_inquirer: 'OptimismInquirer',
        tx_hash: EVMTxHash,
        transactions: EvmTransactions | None = None,
        relevant_address: ChecksumAddress | None = None,
        load_global_caches: list[str] | None = None,
) -> tuple[list['EvmEvent'], OptimismTransactionDecoder]:
    ...


@overload
def get_decoded_events_of_transaction(
        evm_inquirer: 'ArbitrumOneInquirer',
        tx_hash: EVMTxHash,
        transactions: EvmTransactions | None = None,
        relevant_address: ChecksumAddress | None = None,
        load_global_caches: list[str] | None = None,
) -> tuple[list['EvmEvent'], ArbitrumOneTransactionDecoder]:
    ...


@overload
def get_decoded_events_of_transaction(
        evm_inquirer: 'BaseInquirer',
        tx_hash: EVMTxHash,
        transactions: EvmTransactions | None = None,
        relevant_address: ChecksumAddress | None = None,
        load_global_caches: list[str] | None = None,
) -> tuple[list['EvmEvent'], BaseTransactionDecoder]:
    ...


@overload
def get_decoded_events_of_transaction(
        evm_inquirer: 'GnosisInquirer',
        tx_hash: EVMTxHash,
        transactions: EvmTransactions | None = None,
        relevant_address: ChecksumAddress | None = None,
        load_global_caches: list[str] | None = None,
) -> tuple[list['EvmEvent'], GnosisTransactionDecoder]:
    ...


@overload
def get_decoded_events_of_transaction(
        evm_inquirer: 'PolygonPOSInquirer',
        tx_hash: EVMTxHash,
        transactions: EvmTransactions | None = None,
        relevant_address: ChecksumAddress | None = None,
        load_global_caches: list[str] | None = None,
) -> tuple[list['EvmEvent'], PolygonPOSTransactionDecoder]:
    ...


@overload
def get_decoded_events_of_transaction(
        evm_inquirer: 'ScrollInquirer',
        tx_hash: EVMTxHash,
        transactions: EvmTransactions | None = None,
        relevant_address: ChecksumAddress | None = None,
        load_global_caches: list[str] | None = None,
) -> tuple[list['EvmEvent'], ScrollTransactionDecoder]:
    ...


@overload
def get_decoded_events_of_transaction(
        evm_inquirer: 'BinanceSCInquirer',
        tx_hash: EVMTxHash,
        transactions: EvmTransactions | None = None,
        relevant_address: ChecksumAddress | None = None,
        load_global_caches: list[str] | None = None,
) -> tuple[list['EvmEvent'], BinanceSCTransactionDecoder]:
    ...


def get_decoded_events_of_transaction(
        evm_inquirer: 'EvmNodeInquirer',
        tx_hash: EVMTxHash,
        transactions: EvmTransactions | None = None,
        relevant_address: ChecksumAddress | None = None,
        load_global_caches: list[str] | None = None,
        evm_decoder: 'EVMTransactionDecoder|None' = None,
) -> tuple[list['EvmEvent'], 'EVMTransactionDecoder']:
    """A convenience function to ask get transaction, receipt and decoded event for a tx_hash

    It also accepts `transactions` in case the caller wants to apply some mocks (like call_count)
    on that object. Same thing for evm_decoder if the callers want to use it before
    for any reason.

    If relevant_address is provided then the added transactions are added linked to
    the provided address.

    Also asserts that _process_swaps is called whenever a transaction contains TRADE events.

    Returns the list of decoded events and the EVMTransactionDecoder
    """
    chain_mappings = {
        ChainID.ETHEREUM: (EthereumTransactions, EthereumTransactionDecoder),
        ChainID.OPTIMISM: (OptimismTransactions, OptimismTransactionDecoder),
        ChainID.POLYGON_POS: (PolygonPOSTransactions, PolygonPOSTransactionDecoder),
        ChainID.ARBITRUM_ONE: (ArbitrumOneTransactions, ArbitrumOneTransactionDecoder),
        ChainID.BASE: (BaseTransactions, BaseTransactionDecoder),
        ChainID.GNOSIS: (GnosisTransactions, GnosisTransactionDecoder),
        ChainID.SCROLL: (ScrollTransactions, ScrollTransactionDecoder),
        ChainID.BINANCE_SC: (BinanceSCTransactions, BinanceSCTransactionDecoder),
    }
    mappings_result = chain_mappings.get(evm_inquirer.chain_id)
    if mappings_result is not None:
        if transactions is None:
            transactions = mappings_result[0](evm_inquirer, evm_inquirer.database)
        if evm_decoder is None:
            decoder: EVMTransactionDecoder = mappings_result[1](evm_inquirer.database, evm_inquirer, transactions)  # noqa: E501
        else:
            decoder = evm_decoder

    else:
        raise AssertionError('Unsupported chainID at tests')

    if relevant_address is not None:
        with evm_inquirer.database.conn.read_ctx() as cursor:
            transactions.get_or_create_transaction(
                cursor=cursor,
                tx_hash=tx_hash,
                relevant_address=relevant_address,
            )

    transactions.get_or_query_transaction_receipt(tx_hash=tx_hash)
    original_run_all_post_decoding_rules = decoder.run_all_post_decoding_rules
    expected_call_count = 0

    def mock_run_all_post_decoding_rules(**kwargs):
        """Increment expected_call_count when a transaction with swaps is encountered."""
        nonlocal expected_call_count
        events, maybe_modified = original_run_all_post_decoding_rules(**kwargs)
        if (
            maybe_modified is True or
            len([e for e in events if e.event_type == HistoryEventType.TRADE]) > 0
        ):
            expected_call_count += 1

        return events, maybe_modified

    with (
        patch_decoder_reload_data(load_global_caches),
        patch.object(decoder, 'run_all_post_decoding_rules', side_effect=mock_run_all_post_decoding_rules),  # noqa: E501
        patch.object(decoder, '_process_swaps', wraps=decoder._process_swaps) as process_swaps_mock,  # noqa: E501
    ):
        result = decoder.decode_and_get_transaction_hashes(ignore_cache=True, tx_hashes=[tx_hash])

    assert process_swaps_mock.call_count >= expected_call_count, 'Encountered unprocessed swaps. Check that all decoders set the process_swaps flag properly.'  # noqa: E501
    return result, decoder
