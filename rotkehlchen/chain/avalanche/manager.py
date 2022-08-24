import logging
from typing import Any, Dict, List, Optional
from eth_utils import to_checksum_address
from web3 import HTTPProvider, Web3
from web3.datastructures import MutableAttributeDict
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.covalent import Covalent
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_str

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

WEB3_LOGQUERY_BLOCK_RANGE = 250000


class AvalancheManager():
    def __init__(
            self,
            avaxrpc_endpoint: str,
            covalent: Covalent,
            msg_aggregator: MessagesAggregator,
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        log.debug(f'Initializing Avalanche Manager with own rpc endpoint: {avaxrpc_endpoint}')
        self.rpc_timeout = rpc_timeout
        self.w3 = Web3(
            HTTPProvider(
                endpoint_uri=avaxrpc_endpoint,
                request_kwargs={'timeout': self.rpc_timeout},
            ),
        )
        self.covalent = covalent
        self.msg_aggregator = msg_aggregator

    def connected_to_any_web3(self) -> bool:
        return self.w3.isConnected()

    def get_latest_block_number(self) -> int:
        return self.w3.eth.block_number

    def get_avax_balance(self, account: ChecksumEvmAddress) -> FVal:
        """Gets the balance of the given account in AVAX

        May raise:
        - RemoteError if Covalent is used and there is a problem querying it or
        parsing its response
        """
        result = self.covalent.get_token_balances_address(account)
        if result is None:
            balance = from_wei(FVal(self.w3.eth.get_balance(account)))
        else:
            balance = ZERO
            for entry in result:
                if entry.get('contract_ticker_symbol') == 'AVAX':
                    balance = from_wei(FVal(entry.get('balance', 0)))
                    break
            if balance == ZERO:
                balance = from_wei(FVal(self.w3.eth.get_balance(account)))
        return FVal(balance)

    def get_multiavax_balance(
            self,
            accounts: List[ChecksumEvmAddress],
    ) -> Dict[ChecksumEvmAddress, FVal]:
        """Returns a dict with keys being accounts and balances in AVAX

        May raise:
        - RemoteError if an external service such as Covalent is queried and
          there is a problem with its query.
        """
        balances = {}
        for account in accounts:
            balances[account] = self.get_avax_balance(account)
        return balances

    def get_block_by_number(self, num: int) -> Dict[str, Any]:
        """Returns the block object corresponding to the given block number

        May raise:
        - RemoteError if an external service such as Covalent is queried and
        there is a problem with its query.
        - BlockNotFound if number used to lookup the block can't be found. Raised
        by web3.eth.get_block().
        """
        block_data: MutableAttributeDict = MutableAttributeDict(self.w3.eth.get_block(num))  # type: ignore # pylint: disable=no-member  # noqa: E501
        block_data['hash'] = hex_or_bytes_to_str(block_data['hash'])
        return dict(block_data)

    def get_code(self, account: ChecksumEvmAddress) -> str:
        """Gets the deployment bytecode at the given address

        May raise:
        - RemoteError if Covalent is used and there is a problem querying it or
        parsing its response
        """
        return hex_or_bytes_to_str(self.w3.eth.getCode(account))

    def get_transaction_receipt(
            self,
            tx_hash: EVMTxHash,
    ) -> Dict[str, Any]:
        tx_receipt = self.covalent.get_transaction_receipt(tx_hash)
        if tx_receipt is None:
            tx_receipt = self.w3.eth.get_transaction(tx_hash).__dict__  # type: ignore
            tx_receipt['hash'] = EVMTxHash(tx_receipt['hash'])  # web3 returns HexBytes
            return tx_receipt
        try:
            # Turn hex numbers to int
            tx_receipt.pop('from_address_label', None)
            tx_receipt.pop('to_address_label', None)
            block_number = tx_receipt['block_height']
            tx_receipt['blockNumber'] = tx_receipt.pop('block_height', None)
            tx_receipt['cumulativeGasUsed'] = tx_receipt.pop('gas_spent', None)
            tx_receipt['gasUsed'] = tx_receipt['cumulativeGasUsed']
            successful = tx_receipt.pop('successful', None)
            tx_receipt['status'] = 1 if successful else 0
            tx_receipt['transactionIndex'] = 0
            txhash = tx_receipt.pop('tx_hash')
            tx_receipt['hash'] = deserialize_evm_tx_hash(txhash)  # covalent returns string
            tx_receipt['from'] = to_checksum_address(tx_receipt['from_address'])
            tx_receipt['to'] = to_checksum_address(tx_receipt['to_address'])
            tx_receipt['gasPrice'] = tx_receipt['gas_price']
            tx_receipt['gas'] = tx_receipt['gas_offered']

            # TODO input and nonce is decoded in Covalent api, encoded in future
            tx_receipt['input'] = '0x'
            tx_receipt['nonce'] = 0
            for index, receipt_log in enumerate(tx_receipt['log_events']):
                receipt_log['blockNumber'] = block_number
                receipt_log['logIndex'] = receipt_log.pop('log_offset', None)
                receipt_log['transactionIndex'] = 0
                tx_receipt['log_events'][index] = receipt_log
        except (DeserializationError, ValueError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'missing key entry for {msg}'

            raise RemoteError(
                f'Couldnt deserialize transaction receipt data from '
                f'covalent {tx_receipt} due to {msg}',
            ) from e
        return tx_receipt

    def call_contract(
            self,
            contract_address: ChecksumEvmAddress,
            abi: List,
            method_name: str,
            arguments: Optional[List[Any]] = None,
    ) -> Any:
        """Performs an eth_call to an ethereum contract

        May raise:
        - RemoteError if Covalent is used and there is a problem with
        reaching it or with the returned result
        - BlockchainQueryError if web3 is used and there is a VM execution error
        """

        contract = self.w3.eth.contract(address=contract_address, abi=abi)
        try:
            method = getattr(contract.caller, method_name)
            result = method(*arguments if arguments else [])
        except (ValueError, BadFunctionCallOutput) as e:
            raise BlockchainQueryError(
                f'Error doing call on contract {contract_address}: {str(e)}',
            ) from e
        return result

    @staticmethod
    def get_basic_contract_info(address: ChecksumEvmAddress) -> Dict[str, Any]:
        """
        Query a contract address in pangolin graph node and return basic information as:
        - Decimals
        - name
        - symbol
        if it is provided in the contract. This method may raise:
        - BadFunctionCallOutput: If there is an error calling a bad address
        """
        properties = ('decimals', 'symbol', 'name')
        info: Dict[str, Any] = {}
        try:
            # Output contains call status and result
            graph = Graph('https://api.thegraph.com/subgraphs/name/dasconnor/pangolin-dex')
            output = graph.query(
                f'''{{token(id:"{address.lower()}"){{
                    symbol
                    name
                    decimals
                    }}
                }}
                ''',
            )
            token = output['token']
            for prop in properties:
                if prop == 'decimals':
                    info[prop] = int(token[prop])
                else:
                    info[prop] = token[prop]
        except (KeyError, ValueError, TypeError):
            # If something happens in the connection the output should have
            # the same length as the tuple of properties
            return {'decimals': None, 'symbol': None, 'name': None}
        return info
