import logging
from typing import TYPE_CHECKING, Any

import requests

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.types import NodeName
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import StarknetAddress, SupportedBlockchain, Timestamp

from .constants import DEFAULT_STARKNET_RPC_ENDPOINT, STRK_TOKEN_ADDRESS
from .types import StarknetTransaction
from .utils import normalize_starknet_address, wei_to_strk

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.voyager import Voyager
    from rotkehlchen.greenlets.manager import GreenletManager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def starknet_keccak(data: bytes) -> int:
    """
    Calculate Starknet keccak hash of data.
    Uses the web3.py keccak implementation which rotki already has.

    Returns the hash as an integer, masked to 250 bits for Starknet field elements.
    """
    from eth_utils import keccak
    hash_bytes = keccak(data)
    # Convert to integer
    hash_int = int.from_bytes(hash_bytes, byteorder='big')
    # Mask to 250 bits (Starknet field element constraint: values < 2^251)
    mask = (1 << 250) - 1
    return hash_int & mask


def get_selector_from_name(func_name: str) -> str:
    """
    Calculate the Starknet selector for a function name.
    Returns the selector as a hex string with 0x prefix.
    """
    selector_int = starknet_keccak(func_name.encode('ascii'))
    return hex(selector_int)


class StarknetInquirer:
    """Handles all Starknet RPC queries using direct HTTP calls"""

    def __init__(
            self,
            greenlet_manager: 'GreenletManager',
            database: 'DBHandler',
            voyager: 'Voyager',
    ) -> None:
        self.greenlet_manager = greenlet_manager
        self.database = database
        self.voyager = voyager
        self.blockchain = SupportedBlockchain.STARKNET
        self.rpc_timeout = DEFAULT_RPC_TIMEOUT
        self.rpc_endpoint = DEFAULT_STARKNET_RPC_ENDPOINT
        self.failed_to_connect_nodes: set[str] = set()

        # Cache commonly used selectors
        self._balance_of_selector = get_selector_from_name('balanceOf')
        log.debug(f'Initialized Starknet inquirer with balanceOf selector: {self._balance_of_selector}')  # noqa: E501

    def get_connected_nodes(self) -> list[NodeName]:
        """Get all currently connected nodes.

        For Starknet we use a single RPC endpoint, so we return it as a
        single-element list when the endpoint is configured.
        """
        return [NodeName(
            name='starknet rpc',
            endpoint=self.rpc_endpoint,
            owned=False,
            blockchain=self.blockchain,
        )]

    def _rpc_call(self, method: str, params: list[Any] | dict[str, Any]) -> Any:
        """Make a JSON-RPC call to the Starknet node

        May raise:
        - RemoteError if there's an issue with the RPC call
        """
        try:
            payload = {
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
                'id': 1,
            }
            log.debug(f'Making Starknet RPC call: {method} to {self.rpc_endpoint}')

            response = requests.post(
                self.rpc_endpoint,
                json=payload,
                timeout=self.rpc_timeout,
                headers={'Content-Type': 'application/json'},
            )
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                error_msg = data['error'].get('message', str(data['error']))
                log.error(f'Starknet RPC error: {error_msg}')
                raise RemoteError(f'Starknet RPC error: {error_msg}')

            return data.get('result')

        except requests.exceptions.RequestException as e:
            log.error(f'Starknet RPC call failed for method {method}: {e}')
            raise RemoteError(f'Starknet RPC call failed: {e}') from e

    def call_contract(
            self,
            contract_address: str,
            entry_point_selector: str,
            calldata: list[str],
    ) -> list[str]:
        """
        Call a Starknet contract view function using starknet_call

        May raise:
        - RemoteError if there's an issue with the RPC call
        """
        try:
            log.debug(
                f'Calling Starknet contract {contract_address} '
                f'selector {entry_point_selector} calldata {calldata}',
            )

            result = self._rpc_call(
                'starknet_call',
                [
                    {
                        'contract_address': contract_address,
                        'entry_point_selector': entry_point_selector,
                        'calldata': calldata,
                    },
                    'latest',  # Use latest block
                ],
            )

            if result is None:
                return []

            return result if isinstance(result, list) else [result]

        except RemoteError:
            raise
        except Exception as e:
            log.error(f'Failed to call contract {contract_address}: {e}')
            raise RemoteError(f'Failed to call contract: {e}') from e

    def get_balance(self, address: StarknetAddress) -> FVal:
        """Query the native STRK balance for an address

        Calls the balanceOf function on the STRK token contract

        May raise:
        - RemoteError if there's an issue querying the RPC
        """
        try:
            normalized_address = normalize_starknet_address(address)
            log.debug(f'Querying Starknet STRK balance for {normalized_address}')

            # Call balanceOf on the STRK token contract
            # balanceOf takes one parameter: the account address
            result = self.call_contract(
                contract_address=STRK_TOKEN_ADDRESS,
                entry_point_selector=self._balance_of_selector,
                calldata=[normalized_address],
            )

            if not result:
                log.debug(f'No balance returned for {address}, returning 0')
                return FVal(0)

            log.debug(f'Raw balance result from Starknet: {result}')

            # Starknet returns uint256 as two felt252 values (low, high)
            # The balance is computed as: low + high * 2**128
            if len(result) >= 2:
                low = int(result[0], 16) if isinstance(result[0], str) else int(result[0])
                high = int(result[1], 16) if isinstance(result[1], str) else int(result[1])
                balance_wei = low + (high * (2 ** 128))
            else:
                # Single value returned
                balance_wei = int(result[0], 16) if isinstance(result[0], str) else int(result[0])

            balance_strk = wei_to_strk(balance_wei)
            log.info(f'Starknet balance for {address}: {balance_strk} STRK ({balance_wei} wei)')
        except RemoteError:
            raise
        except Exception as e:
            log.error(f'Failed to query Starknet balance for {address}: {e}')
            raise RemoteError(f'Failed to query Starknet balance: {e}') from e
        else:
            return balance_strk

    def get_token_balance(
            self,
            address: StarknetAddress,
            token_address: str,
            decimals: int = 18,
    ) -> FVal:
        """Query the balance of a specific token for an address

        Calls the balanceOf function on the specified token contract

        May raise:
        - RemoteError if there's an issue querying the RPC
        """
        try:
            normalized_address = normalize_starknet_address(address)
            normalized_token = normalize_starknet_address(token_address)

            log.debug(f'Querying Starknet token balance for {normalized_address} token {normalized_token}')  # noqa: E501

            # Call balanceOf on the token contract
            result = self.call_contract(
                contract_address=normalized_token,
                entry_point_selector=self._balance_of_selector,
                calldata=[normalized_address],
            )

            if not result:
                return FVal(0)

            # Parse uint256 result (low, high)
            if len(result) >= 2:
                low = int(result[0], 16) if isinstance(result[0], str) else int(result[0])
                high = int(result[1], 16) if isinstance(result[1], str) else int(result[1])
                balance_raw = low + (high * (2 ** 128))
            else:
                balance_raw = int(result[0], 16) if isinstance(result[0], str) else int(result[0])

            # Convert from raw units to token units based on decimals
            balance = FVal(balance_raw) / FVal(10 ** decimals)

            log.debug(f'Token balance for {address}: {balance} (raw: {balance_raw})')
        except RemoteError:
            raise
        except Exception as e:
            log.error(f'Failed to query Starknet token balance for {address} token {token_address}: {e}')  # noqa: E501
            raise RemoteError(f'Failed to query Starknet token balance: {e}') from e
        else:
            return balance

    def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any]:
        """Get the receipt for a transaction by hash.

        May raise:
        - RemoteError if there's an issue with the RPC call
        """
        result = self._rpc_call('starknet_getTransactionReceipt', [tx_hash])
        if result is None:
            raise RemoteError(f'No receipt found for Starknet transaction {tx_hash}')
        return result

    def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        """Get a transaction by hash.

        May raise:
        - RemoteError if there's an issue with the RPC call
        """
        result = self._rpc_call('starknet_getTransactionByHash', [tx_hash])
        if result is None:
            raise RemoteError(f'No transaction found for Starknet hash {tx_hash}')
        return result

    def get_block_with_tx_hashes(self, block_id: str | int) -> dict[str, Any]:
        """Get a block with transaction hashes.

        May raise:
        - RemoteError if there's an issue with the RPC call
        """
        if isinstance(block_id, int):
            block_param = {'block_number': block_id}
        else:
            block_param = {'block_hash': block_id}

        result = self._rpc_call('starknet_getBlockWithTxHashes', [block_param])
        if result is None:
            raise RemoteError(f'No block found for Starknet block_id {block_id}')
        return result

    def get_transaction_for_hash(self, tx_hash: str) -> StarknetTransaction:
        """Fetch a full StarknetTransaction by combining transaction data and receipt.

        May raise:
        - RemoteError if there's an issue querying the RPC
        """
        tx_data = self.get_transaction(tx_hash)
        receipt = self.get_transaction_receipt(tx_hash)

        # Extract sender address
        from_address = StarknetAddress(
            normalize_starknet_address(tx_data.get('sender_address', '0x0')),
        )

        # Extract contract address for INVOKE transactions
        to_address_raw = tx_data.get('contract_address') or tx_data.get('sender_address')
        to_address = StarknetAddress(
            normalize_starknet_address(to_address_raw),
        ) if to_address_raw else None

        # Parse calldata
        calldata = tx_data.get('calldata', [])

        # Extract fee information
        actual_fee_data = receipt.get('actual_fee', {})
        if isinstance(actual_fee_data, dict):
            actual_fee = int(actual_fee_data.get('amount', '0x0'), 16)
        else:
            actual_fee = int(actual_fee_data, 16) if actual_fee_data else 0

        max_fee_raw = tx_data.get('max_fee', '0x0')
        max_fee = int(max_fee_raw, 16) if isinstance(max_fee_raw, str) else int(max_fee_raw)

        # Determine status from receipt
        execution_status = receipt.get('execution_status', 'SUCCEEDED')
        finality_status = receipt.get('finality_status', 'ACCEPTED_ON_L2')
        status = f'{finality_status}'
        if execution_status != 'SUCCEEDED':
            status = f'{execution_status}'

        # Get block info
        block_number = receipt.get('block_number', 0)
        # Block timestamp requires fetching the block; use 0 as placeholder if not in receipt
        block_timestamp = Timestamp(0)

        # Transaction type
        tx_type = tx_data.get('type', 'INVOKE')

        # Extract entry point selector for INVOKE transactions
        selector = tx_data.get('entry_point_selector')

        return StarknetTransaction(
            transaction_hash=tx_hash,
            block_number=block_number,
            block_timestamp=block_timestamp,
            from_address=from_address,
            to_address=to_address,
            selector=selector,
            calldata=calldata,
            max_fee=max_fee,
            actual_fee=actual_fee,
            status=status,
            transaction_type=tx_type,
        )
