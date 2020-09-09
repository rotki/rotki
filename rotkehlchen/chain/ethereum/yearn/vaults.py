from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rotkehlchen.constants.ethereum import EthereumConstants
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

YEARN_YCRV_VAULT = EthereumConstants().contract('YEARN_YCRV_VAULT')
YEARN_DAI_VAULT = EthereumConstants().contract('YEARN_DAI_VAULT')
YEARN_WETH_VAULT = EthereumConstants().contract('YEARN_WETH_VAULT')
YEARN_YFI_VAULT = EthereumConstants().contract('YEARN_YFI_VAULT')
YEARN_ALINK_VAULT = EthereumConstants().contract('YEARN_ALINK_VAULT')
YEARN_USDT_VAULT = EthereumConstants().contract('YEARN_USDT_VAULT')
YEARN_USDC_VAULT = EthereumConstants().contract('YEARN_USDC_VAULT')
YEARN_TUSD_VAULT = EthereumConstants().contract('YEARN_TUSD_VAULT')
YEARN_BCURVE_VAULT = EthereumConstants().contract('YEARN_BCURVE_VAULT')
YEARN_SRENCURVE_VAULT = EthereumConstants().contract('YEARN_SRENCURVE_VAULT')

YEARN_VAULTS = [
    YEARN_YCRV_VAULT,
    YEARN_DAI_VAULT,
    YEARN_WETH_VAULT,
    YEARN_YFI_VAULT,
    YEARN_ALINK_VAULT,
    YEARN_USDT_VAULT,
    YEARN_USDC_VAULT,
    YEARN_TUSD_VAULT,
    YEARN_BCURVE_VAULT,
    YEARN_SRENCURVE_VAULT,
]


class YearnVaults(EthereumModule):

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: DBHandler,
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium

    def get_history(
            self,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,  # pylint: disable=unused-argument
            to_timestamp: Timestamp,  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        pass  # TODO

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
