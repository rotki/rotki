from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.giveth.balances import GivethCommonBalances
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.giveth.constants import GIV_TOKEN_ID

if TYPE_CHECKING:
    from rotkehlchen.chain.gnosis.decoding.decoder import GnosisTransactionDecoder
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer


class GivethBalances(GivethCommonBalances):
    def __init__(
            self,
            evm_inquirer: 'GnosisInquirer',
            tx_decoder: 'GnosisTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            staking_address=string_to_evm_address('0xfFBAbEb49be77E5254333d5fdfF72920B989425f'),
            query_method='balanceOf',
            giv_token_id=GIV_TOKEN_ID,
        )
