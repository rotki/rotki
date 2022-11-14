import json
import logging
import random
from abc import ABCMeta, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from urllib.parse import urlparse

import requests
from ens import ENS
from eth_abi.exceptions import InsufficientDataBytes
from eth_typing import BlockNumber
from web3 import HTTPProvider, Web3
from web3._utils.abi import get_abi_output_types
from web3._utils.contracts import find_matching_event_abi
from web3._utils.filters import construct_event_filter_params
from web3.datastructures import MutableAttributeDict
from web3.exceptions import (
    BadFunctionCallOutput,
    BadResponseFormat,
    BlockNotFound,
    TransactionNotFound,
)
from web3.types import BlockIdentifier, FilterParams

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.ethereum.types import NodeName, WeightedNode
from rotkehlchen.chain.ethereum.utils import MULTICALL_CHUNKS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ONE
from rotkehlchen.constants.ethereum import ERC20TOKEN_ABI, ERC721TOKEN_ABI, UNIV1_LP_ABI
from rotkehlchen.errors.misc import BlockchainQueryError, NotERC721Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_evm_transaction,
    deserialize_int_from_hex,
)
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import (
    SUPPORTED_BLOCKCHAIN_TO_CHAINID,
    ChecksumEvmAddress,
    EvmTokenKind,
    EvmTransaction,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, get_chunks, hex_or_bytes_to_str
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import EvmNodeInquirer
    from .tokens import EvmTokens
    from .transactions import EvmTransactions

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EvmManager(metaclass=ABCMeta):
    """EvmManager defines a basic implementation for EVM chains."""
    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            transactions: 'EvmTransactions',
            tokens: 'EvmTokens',
    ) -> None:
        super().__init__()
        self.node_inquirer = node_inquirer
        self.transactions = transactions
        self.tokens = tokens

    def get_historical_balance(
            self,
            address: ChecksumEvmAddress,
            block_number: int,
    ) -> Optional[FVal]:
        """Attempts to get a historical eth balance from the local own node only.
        If there is no node or the node can't query historical balance (not archive) then
        returns None"""
        return self.node_inquirer.get_historical_balance(address, block_number)
