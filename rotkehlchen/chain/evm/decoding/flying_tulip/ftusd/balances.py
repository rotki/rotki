"""Pending FT rewards of Flying Tulip's sftUSD staking vault."""
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import get_or_create_evm_token, token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import CPT_FLYING_TULIP
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import FLYING_TULIP_FTUSD_DEPLOYMENTS, STAKING_VAULT_ABI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class FlyingTulipStakingBalances(ProtocolWithBalance):
    """Expose FT rewards claimable from the sftUSD staking vault as balances.

    The sftUSD shares themselves are a regular ERC-20 already covered by normal
    token detection, so only the not-yet-claimed FT rewards are added here.
    """

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            tx_decoder: EVMTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_FLYING_TULIP,
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED),
            },
        )
        self.deployment = FLYING_TULIP_FTUSD_DEPLOYMENTS[evm_inquirer.chain_id]
        self.staking_vault = EvmContract(
            address=self.deployment.staking_vault,
            abi=STAKING_VAULT_ABI,
            deployed_block=0,  # not used for calls
        )

    def query_balances(self) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses := list(dict.fromkeys(self.addresses_with_deposits()))) == 0:
            return balances

        try:
            results = self.evm_inquirer.multicall(calls=[
                (
                    self.staking_vault.address,
                    self.staking_vault.encode(
                        method_name='previewClaimable',
                        arguments=[address],
                    ),
                )
                for address in addresses
            ])
        except RemoteError as e:
            log.error(
                'Failed to query claimable Flying Tulip staking rewards on %s due to %s',
                self.evm_inquirer.chain_name,
                e,
            )
            return balances

        ft_token, amounts = None, []
        for address, result in zip(addresses, results, strict=True):
            try:
                (claimable_raw,) = self.staking_vault.decode(
                    result=result,
                    method_name='previewClaimable',
                    arguments=[address],
                )
            except DeserializationError as e:
                log.error(
                    'Failed to decode claimable Flying Tulip staking rewards of %s on %s due to %s',  # noqa: E501
                    address,
                    self.evm_inquirer.chain_name,
                    e,
                )
                continue

            if claimable_raw == 0:
                continue

            if ft_token is None:
                ft_token = get_or_create_evm_token(
                    userdb=self.evm_inquirer.database,
                    evm_address=self.deployment.ft_token,
                    chain_id=self.evm_inquirer.chain_id,
                )
            amounts.append((address, ft_token, token_normalized_value(
                token_amount=claimable_raw,
                token=ft_token,
            )))

        self._add_priced_balances(balances=balances, amounts=amounts)
        return balances
