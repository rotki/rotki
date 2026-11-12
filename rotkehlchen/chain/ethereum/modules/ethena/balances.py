import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet, ClaimEntry
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

from .constants import CPT_ETHENA, ETHENA_STAKING_ABI, STAKING_VAULTS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthenaBalances(ProtocolWithBalance):
    """Query the tokens of Ethena unstakes that are in their cooldown or waiting for a claim.

    Staked sUSDe and sENA are already counted as wallet tokens. Once a cooldown starts they
    are burned and the underlying USDe or ENA is held by the vault's silo until unstake.
    """

    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EthereumTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_ETHENA,
            deposit_event_types={(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED)},
        )
        # staked token -> (vault contract, underlying token)
        self.vaults = {
            vault.token_id: (
                EvmContract(address=address, abi=ETHENA_STAKING_ABI, deployed_block=0),
                Asset(vault.underlying_token_id),
            ) for address, vault in STAKING_VAULTS.items()
        }

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        # (user address, staked token) of every vault the user has returned staked tokens to
        user_vaults = sorted({
            (address, event.asset.identifier)
            for address, events in self.addresses_with_deposits(location_labels=addresses).items()
            for event in events
            if event.asset.identifier in self.vaults
        })
        if len(user_vaults) == 0:
            return balances

        try:
            results = self.evm_inquirer.multicall(calls=[(
                (contract := self.vaults[token_id][0]).address,
                contract.encode(method_name='cooldowns', arguments=[address]),
            ) for address, token_id in user_vaults])
        except RemoteError as e:
            log.error('Failed to query Ethena unstake cooldowns: %s', e)
            return balances

        cooldowns: list[tuple[ChecksumEvmAddress, Asset, FVal, Timestamp]] = []
        for (address, token_id), result in zip(user_vaults, results, strict=True):
            contract, underlying_asset = self.vaults[token_id]
            try:
                cooldown_end, raw_amount = contract.decode(
                    result=result,
                    method_name='cooldowns',
                    arguments=[address],
                )
            except DeserializationError as e:
                log.error(
                    'Failed to decode Ethena cooldown of %s at %s: %s',
                    address, contract.address, e,
                )
                continue

            if raw_amount == 0:
                continue

            cooldowns.append((
                address,
                underlying_asset,
                token_normalized_value_decimals(
                    token_amount=raw_amount,
                    token_decimals=DEFAULT_TOKEN_DECIMALS,
                ),
                Timestamp(cooldown_end),
            ))

        if len(cooldowns) == 0:
            return balances

        prices = Inquirer.find_main_currency_prices(list({asset for _, asset, _, _ in cooldowns}))
        for address, asset, amount, cooldown_end in cooldowns:
            balances[address].assets[asset][self.counterparty] += Balance(
                amount=amount,
                value=amount * prices.get(asset, ZERO_PRICE),
                awaiting_claim=amount,
                claims=(ClaimEntry(amount=amount, available_at=cooldown_end),),
            )

        return balances
