import logging
from abc import ABC
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.evm.contracts import EvmContract, EvmContracts
from rotkehlchen.chain.evm.l2_with_l1_fees.etherscan import L2WithL1FeesEtherscan
from rotkehlchen.chain.evm.l2_with_l1_fees.types import SupportedL2WithL1FeesType
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.proxies_inquirer import EvmProxiesInquirer
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.externalapis.utils import maybe_read_integer
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class L2WithL1FeesInquirer(EvmNodeInquirer, ABC):
    """
    An intermediary node inquirer class to be inherited by L2 chains
    that have an extra L1 Fee structure.
    """
    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: L2WithL1FeesEtherscan,
            blockchain: SupportedL2WithL1FeesType,
            contracts: EvmContracts,
            rpc_timeout: int,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            native_token: CryptoAsset,
            blockscout: Blockscout | None = None,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=blockchain,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contract_multicall,
            contract_scan=contract_scan,
            native_token=native_token,
            blockscout=blockscout,
        )

    def _additional_receipt_processing(self, tx_receipt: dict[str, Any]) -> None:
        """Performs additional tx_receipt processing where necessary

        May raise:
            - DeserializationError if it can't convert a value to an int or if an unexpected
            type is given.
            - KeyError if tx_receipt has no l1Fee entry
        """
        tx_receipt['l1Fee'] = maybe_read_integer(data=tx_receipt, key='l1Fee', api=f'web3 {self.blockchain.name.lower()}')  # noqa: E501


class DSProxyL2WithL1FeesInquirerWithCacheData(L2WithL1FeesInquirer, ABC):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: L2WithL1FeesEtherscan,
            blockchain: SupportedL2WithL1FeesType,
            contracts: EvmContracts,
            rpc_timeout: int,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            dsproxy_registry: 'EvmContract',
            native_token: CryptoAsset,
            blockscout: Blockscout | None = None,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=blockchain,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contract_multicall,
            contract_scan=contract_scan,
            native_token=native_token,
            blockscout=blockscout,
        )
        self.proxies_inquirer = EvmProxiesInquirer(
            node_inquirer=self,
            dsproxy_registry=dsproxy_registry,
        )
