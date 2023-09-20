import logging
from abc import ABCMeta
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.evm.contracts import EvmContract, EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer, UpdatableCacheDataMixin
from rotkehlchen.chain.evm.proxies_inquirer import EvmProxiesInquirer
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.chain.optimism_superchain.etherscan import OptimismSuperchainEtherscan
from rotkehlchen.externalapis.utils import maybe_read_integer
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismSuperchainInquirer(EvmNodeInquirer, metaclass=ABCMeta):
    """
    An intermediary node inquirer class to be inherited by chains based on the Optimism Superchain.

    Provides support for handling the layer 1 fee structure common to optimism-based chains.
    """
    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: OptimismSuperchainEtherscan,
            blockchain: Literal[
                SupportedBlockchain.OPTIMISM,
                SupportedBlockchain.BASE,
            ],
            etherscan_node: WeightedNode,
            etherscan_node_name: str,
            contracts: EvmContracts,
            rpc_timeout: int,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            native_token: CryptoAsset,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=blockchain,
            etherscan_node=etherscan_node,
            etherscan_node_name=etherscan_node_name,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contract_multicall,
            contract_scan=contract_scan,
            native_token=native_token,
        )

    def _additional_receipt_processing(self, tx_receipt: dict[str, Any]) -> None:
        """Performs additional tx_receipt processing where necessary

        May raise:
            - DeserializationError if it can't convert a value to an int or if an unexpected
            type is given.
            - KeyError if tx_receipt has no l1Fee entry
        """
        tx_receipt['l1Fee'] = maybe_read_integer(data=tx_receipt, key='l1Fee', api=f'web3 {self.blockchain.name.lower()}')  # noqa: E501


class DSProxyOptimismSuperchainInquirerWithCacheData(OptimismSuperchainInquirer, UpdatableCacheDataMixin, metaclass=ABCMeta):  # noqa: E501

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: OptimismSuperchainEtherscan,
            blockchain: Literal[
                SupportedBlockchain.OPTIMISM,
                SupportedBlockchain.BASE,
            ],
            etherscan_node: WeightedNode,
            etherscan_node_name: str,
            contracts: EvmContracts,
            rpc_timeout: int,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            dsproxy_registry: 'EvmContract',
            native_token: CryptoAsset,
    ) -> None:
        UpdatableCacheDataMixin.__init__(self, database)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=blockchain,
            etherscan_node=etherscan_node,
            etherscan_node_name=etherscan_node_name,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contract_multicall,
            contract_scan=contract_scan,
            native_token=native_token,
        )
        self.proxies_inquirer = EvmProxiesInquirer(
            node_inquirer=self,
            dsproxy_registry=dsproxy_registry,
        )
