"""Current Frankencoin savings positions."""
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import get_or_create_evm_token, token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.frankencoin.constants import CPT_FRANKENCOIN, ZCHF_ADDRESS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import SAVINGS_CONTRACT_ABI, SAVINGS_CONTRACT_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class FrankencoinSavingsBalances(ProtocolWithBalance):
    """Query deposited savings and expose them as balances of the underlying asset."""

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            tx_decoder: EVMTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_FRANKENCOIN,
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
            },
        )
        self.savings_contract = EvmContract(
            address=SAVINGS_CONTRACT_ADDRESS[evm_inquirer.chain_id],
            abi=SAVINGS_CONTRACT_ABI,
            deployed_block=0,  # not used for calls
        )
        self.zchf = get_or_create_evm_token(
            userdb=evm_inquirer.database,
            evm_address=ZCHF_ADDRESS[evm_inquirer.chain_id],
            chain_id=evm_inquirer.chain_id,
        )

    def query_balances(self) -> BalancesSheetType:
        """Return deposited ZCHF plus accrued interest for addresses with prior deposits."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses := list(self.addresses_with_deposits())) == 0:
            return balances

        # Calls are interleaved so every two responses belong to the same address.
        calls = [
            (
                self.savings_contract.address,
                self.savings_contract.encode(method_name=method_name, arguments=[address]),
            )
            for address in addresses
            for method_name in ('savings', 'accruedInterest')
        ]

        try:
            results = self.evm_inquirer.multicall(calls=calls)
            if len(results) != len(calls):
                log.error(
                    'Unexpected response count from Frankencoin Savings contract %s on %s. '
                    'Expected %s but got %s',
                    self.savings_contract.address,
                    self.evm_inquirer.chain_name,
                    len(calls),
                    len(results),
                )
                return balances
        except RemoteError as e:
            log.error(
                'Failed to query Frankencoin Savings balances on %s due to %s',
                self.evm_inquirer.chain_name,
                e,
            )
            return balances

        amounts = []
        for address, savings_result, interest_result in zip(
            addresses,
            results[::2],
            results[1::2],
            strict=True,
        ):
            try:
                saved_raw, _, referrer, referral_fee_ppm = self.savings_contract.decode(
                    result=savings_result,
                    method_name='savings',
                    arguments=[address],
                )
                (interest_raw,) = self.savings_contract.decode(
                    result=interest_result,
                    method_name='accruedInterest',
                    arguments=[address],
                )
            except DeserializationError as e:
                log.error(
                    'Failed to decode Frankencoin Savings balance for %s on %s due to %s',
                    address,
                    self.evm_inquirer.chain_name,
                    e,
                )
                continue

            # Accrued interest is gross; the referral fee is deducted when it is collected.
            referral_fee = (
                interest_raw * referral_fee_ppm // 1_000_000
                if referrer != ZERO_ADDRESS else 0
            )
            if (balance_raw := saved_raw + interest_raw - referral_fee) == 0:
                continue

            amounts.append((address, self.zchf, token_normalized_value_decimals(
                token_amount=balance_raw,
                token_decimals=self.zchf.decimals,
            )))

        self._add_priced_balances(balances=balances, amounts=amounts)
        return balances
