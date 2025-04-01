import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.curve.lend.balances import CurveControllerCommonBalances
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveCrvusdBalances(CurveControllerCommonBalances):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            evm_product=EvmProduct.MINTING,
        )

    def get_collateral_and_borrowed_tokens(
            self,
            controller_address: 'ChecksumEvmAddress',
            controller_contract: EvmContract,
    ) -> tuple['EvmToken', 'EvmToken'] | None:
        """Retrieve the collateral and borrowed tokens for the specified controller.
        For crvUSD controllers the borrowed token will always be crvUSD.
        """
        try:
            return (
                get_or_create_evm_token(
                    userdb=self.evm_inquirer.database,
                    evm_address=deserialize_evm_address(self.evm_inquirer.call_contract(
                        contract_address=controller_address,
                        abi=controller_contract.abi,
                        method_name='collateral_token',
                    )),
                    chain_id=self.evm_inquirer.chain_id,
                ),
                EvmToken('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),  # crvUSD
            )
        except (RemoteError, DeserializationError, NotERC20Conformant, NotERC721Conformant) as e:
            log.error(
                f'Failed to load tokens for Curve crvUSD controller {controller_address} '
                f'on {self.evm_inquirer.chain_name} due to {e!s}',
            )
            return None
