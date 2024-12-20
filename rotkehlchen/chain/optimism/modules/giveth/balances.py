from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.giveth.balances import GivethCommonBalances
from rotkehlchen.chain.optimism.modules.giveth.constants import GIV_TOKEN_ID, GIVPOW_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer


class GivethBalances(GivethCommonBalances):
    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer',
            tx_decoder: 'OptimismTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            staking_address=GIVPOW_ADDRESS,
            query_method='depositTokenBalance',
            giv_token_id=GIV_TOKEN_ID,
        )
