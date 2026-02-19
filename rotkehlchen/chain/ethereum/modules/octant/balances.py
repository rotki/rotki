import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final, cast

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_GLM
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CPT_OCTANT, OCTANT_DEPOSITS, OCTANT_DEPOSITS_V2

if TYPE_CHECKING:
    from eth_typing.abi import ABI

    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

OCTANT_V2_ABI: Final = cast('ABI', [{
    'inputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
    'name': 'depositorTotalStaked',
    'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
    'stateMutability': 'view',
    'type': 'function',
}])


class OctantBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_OCTANT,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},  # noqa: E501
        )
        self.glm = A_GLM.resolve_to_evm_token()

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances of locked GLM in Octant"""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        # fetch deposit events
        if len(addresses_with_deposits := list(self.addresses_with_deposits())) == 0:
            return balances

        deposits_contract = self.evm_inquirer.contracts.contract(OCTANT_DEPOSITS)
        deposits_v2_contract = EvmContract(address=OCTANT_DEPOSITS_V2, abi=OCTANT_V2_ABI)
        try:
            call_output_v1 = self.evm_inquirer.multicall(
                calls=[(
                    deposits_contract.address,
                    deposits_contract.encode(method_name='deposits', arguments=[address]),
                ) for address in addresses_with_deposits],
            )
        except RemoteError as e:
            log.error(f'Failed to query octant locked balances due to {e!s}')
            return balances

        call_output_v2 = None
        try:
            call_output_v2 = self.evm_inquirer.multicall(
                calls=[(
                    deposits_v2_contract.address,
                    deposits_v2_contract.encode(
                        method_name='depositorTotalStaked',
                        arguments=[address],
                    ),
                ) for address in addresses_with_deposits],
            )
        except RemoteError as e:
            # Keep v1 balances if v2 calls fail (e.g. unavailable node/indexer response).
            log.debug(f'Failed to query octant v2 locked balances due to {e!s}')

        v2_raw_balances: dict = {}
        if call_output_v2 is not None:
            if len(call_output_v2) != len(addresses_with_deposits):
                log.error(
                    'Unexpected octant v2 multicall result length. '
                    f'Expected {len(addresses_with_deposits)} got {len(call_output_v2)}.',
                )

            for idx, address in enumerate(addresses_with_deposits):
                if idx >= len(call_output_v2):
                    break
                v2_raw_balances[address] = deposits_v2_contract.decode(
                    call_output_v2[idx],
                    'depositorTotalStaked',
                    arguments=[address],
                )[0]

        glm_price = Inquirer.find_price(
            from_asset=self.glm,
            to_asset=CachedSettings().main_currency,
        )
        for idx, result_v1 in enumerate(call_output_v1):
            address = addresses_with_deposits[idx]
            amount_raw = deposits_contract.decode(result_v1, 'deposits', arguments=[address])[0]
            amount_raw += v2_raw_balances.get(address, 0)
            amount = asset_normalized_value(amount_raw, self.glm)
            if amount == ZERO:
                continue

            balance = Balance(amount=amount, value=glm_price * amount)
            balances[address].assets[self.glm][self.counterparty] += balance

        return balances
