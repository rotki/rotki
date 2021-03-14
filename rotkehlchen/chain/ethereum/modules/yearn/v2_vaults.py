from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import AssetBalance, Balance, DefiEvent, DefiEventType
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.modules.yearn import YearnVaultHistory, YearnVaultBalance
from rotkehlchen.chain.ethereum.structures import YearnVault, YearnVaultEvent, YearnVaults
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants.ethereum import (
    ERC20TOKEN_ABI,
    MAX_BLOCKTIME_CACHE,
    YEARN_3CRV_VAULT,
    YEARN_ALINK_VAULT,
    YEARN_BCURVE_VAULT,
    YEARN_DAI_VAULT,
    YEARN_GUSD_VAULT,
    YEARN_SRENCURVE_VAULT,
    YEARN_TUSD_VAULT,
    YEARN_USDC_VAULT,
    YEARN_USDT_VAULT,
    YEARN_VAULTS_PREFIX,
    YEARN_WETH_VAULT,
    YEARN_YCRV_VAULT,
    YEARN_YFI_VAULT,
    ZERO_ADDRESS,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import SPECIAL_SYMBOLS, Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import address_to_bytes32, hexstr_to_int, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import (
        GIVEN_DEFI_BALANCES,
        DefiProtocolBalances,
    )
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

class YearnV2Vaults(EthereumModule):

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.history_lock = Semaphore()

        try:
            self.graph_inquirer: Optional[YearnV2Inquirer] = YearnV2Inquirer(
                ethereum_manager=ethereum_manager,
                database=database,
                premium=premium,
                msg_aggregator=msg_aggregator
            )
        except RemoteError as e:
            self.graph_inquirer = None
            self.msg_aggregator.add_error(
                f'Could not initialize the Yearn V2 subgraph due to {str(e)}. '
            )

    def _get_single_addr_balance(
            self,
            defi_balances: List['DefiProtocolBalances'],
            roi_cache: Dict[str, FVal],
    ) -> Dict[str, YearnVaultBalance]:
        pass

    def _get_vault_deposit_events(
            self,
            vault: YearnVault,
            address: ChecksumEthAddress,
            from_block: int,
            to_block: int,
    ) -> List[YearnVaultEvent]:
        pass

    def _get_vault_withdraw_events(
            self,
            vault: YearnVault,
            address: ChecksumEthAddress,
            from_block: int,
            to_block: int,
    ) -> List[YearnVaultEvent]:
        pass