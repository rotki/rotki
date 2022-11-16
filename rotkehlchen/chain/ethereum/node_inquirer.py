import logging
from typing import TYPE_CHECKING, Dict, Optional, Sequence, cast

import requests
from eth_typing import BlockNumber
from web3 import Web3

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.constants import ETHERSCAN_NODE
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.modules.eth2.constants import ETH2_DEPOSIT
from rotkehlchen.chain.evm.node_inquirer import WEB3_LOGQUERY_BLOCK_RANGE, EvmNodeInquirer
from rotkehlchen.constants.ethereum import ETH_MULTICALL, ETH_MULTICALL_2, ETH_SCAN
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain, Timestamp
from rotkehlchen.utils.network import request_get_dict

from .types import ETHERSCAN_NODE_NAME, WeightedNode, string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.etherscan import EthereumEtherscan
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BLOCKCYPHER_URL = 'https://api.blockcypher.com/v1/eth/main'


class EthereumInquirer(EvmNodeInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: 'EthereumEtherscan',
            connect_at_start: Sequence[WeightedNode],
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.ETHEREUM,
            etherscan_node=ETHERSCAN_NODE,
            etherscan_node_name=ETHERSCAN_NODE_NAME,
            contract_scan=ETH_SCAN[ChainID.ETHEREUM],
            contract_multicall=ETH_MULTICALL,
            contract_multicall_2=ETH_MULTICALL_2,
            connect_at_start=connect_at_start,
            rpc_timeout=rpc_timeout,
        )
        self.blocks_subgraph = Graph('https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks')  # noqa: E501
        self.etherscan = cast('EthereumEtherscan', self.etherscan)

    # -- Implementation of EvmNodeInquirer base methods --

    def query_highest_block(self) -> BlockNumber:
        log.debug('Querying blockcypher for ETH highest block', url=BLOCKCYPHER_URL)
        eth_resp: Optional[Dict[str, str]]
        try:
            eth_resp = request_get_dict(BLOCKCYPHER_URL)
        except (RemoteError, UnableToDecryptRemoteData, requests.exceptions.RequestException):
            eth_resp = None

        block_number: Optional[int]
        if eth_resp and 'height' in eth_resp:
            block_number = int(eth_resp['height'])
            log.debug('ETH highest block result', block=block_number)
        else:
            block_number = self.etherscan.get_latest_block_number()
            log.debug('ETH highest block result', block=block_number)

        return BlockNumber(block_number)

    def have_archive(self, requery: bool = False) -> bool:
        if self.queried_archive_connection and requery is False:
            return self.archive_connection

        balance = self.get_historical_balance(
            address=string_to_evm_address('0x50532e4Be195D1dE0c2E6DfA46D9ec0a4Fee6861'),
            block_number=87042,
        )
        self.archive_connection = balance is not None and balance == FVal('5.1063307')
        self.queried_archive_connection = True
        return self.archive_connection

    def _get_blocknumber_by_time_from_subgraph(self, ts: Timestamp) -> int:
        """Queries Ethereum Blocks Subgraph for closest block at or before given timestamp"""
        response = self.blocks_subgraph.query(
            f"""
            {{
                blocks(
                    first: 1, orderBy: timestamp, orderDirection: desc,
                    where: {{timestamp_lte: "{ts}"}}
                ) {{
                    id
                    number
                    timestamp
                }}
            }}
            """,
        )
        try:
            result = int(response['blocks'][0]['number'])
        except (IndexError, KeyError) as e:
            raise RemoteError(
                f'Got unexpected ethereum blocks subgraph response: {response}',
            ) from e
        else:
            return result

    def get_blocknumber_by_time(self, ts: Timestamp, etherscan: bool = True) -> int:
        """Searches for the blocknumber of a specific timestamp
        - Performs the etherscan api call by default first
        - If RemoteError raised or etherscan flag set to false
            -> queries blocks subgraph
        """
        if etherscan:
            try:
                return self.etherscan.get_blocknumber_by_time(ts)
            except RemoteError:
                pass

        return self._get_blocknumber_by_time_from_subgraph(ts)

    # -- Implementation of EvmNodeInquirer optional methods --

    def logquery_block_range(
            self,
            web3: Web3,
            contract_address: ChecksumEvmAddress,
    ) -> int:
        """We know that in most of its early life the Eth2 contract address returns a
        a lot of results. So limit the query range to not hit the infura limits every time
        """
        # supress https://lgtm.com/rules/1507386916281/ since it does not apply here
        infura_eth2_log_query = (
            'infura.io' in web3.manager.provider.endpoint_uri and  # type: ignore # noqa: E501 lgtm [py/incomplete-url-substring-sanitization]
            contract_address == ETH2_DEPOSIT.address
        )
        return WEB3_LOGQUERY_BLOCK_RANGE if infura_eth2_log_query is False else 75000
