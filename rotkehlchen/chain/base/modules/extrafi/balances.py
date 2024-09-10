from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.extrafi.balances import ExtrafiCommonBalances

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder


class ExtrafiBalances(ExtrafiCommonBalances):

    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            extrafi_token=Asset('eip155:8453/erc20:0x2dad3a13ef0c6366220f989157009e501e7938f8'),
        )
