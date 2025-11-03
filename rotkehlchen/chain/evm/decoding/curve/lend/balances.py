import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import get_or_create_evm_token, token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.curve.lend.constants import CURVE_VAULT_CONTROLLER_ABI
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import Price

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveControllerCommonBalances(ProtocolWithBalance, ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        """Common balances class for both curve lend and crvusd controllers.
        `evm_product` is used with addresses_with_deposits to get addresses and events for the
        correct type of controller.
        """
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_CURVE,
            deposit_event_types={
                (HistoryEventType.WITHDRAWAL, HistoryEventSubType.GENERATE_DEBT),
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET),
            },
        )

    @abstractmethod
    def get_collateral_and_borrowed_tokens(
            self,
            controller_address: 'ChecksumEvmAddress',
            controller_contract: EvmContract,
    ) -> tuple['EvmToken', 'EvmToken'] | None:
        """Retrieve the collateral and borrowed tokens for the specified controller."""

    def _get_controllers_with_balances(self) -> dict[ChecksumEvmAddress, set[ChecksumEvmAddress]]:
        """Get addresses of controllers that the user may have balances on.
        Returns a dict of controller addresses -> set of user addresses with possible balances.
        """
        controllers: dict[ChecksumEvmAddress, set[ChecksumEvmAddress]] = defaultdict(set)
        for address, events in self.addresses_with_deposits().items():
            for event in events:
                if event.extra_data is None or 'controller_address' not in event.extra_data:
                    continue  # skip any deposits without a controller address

                controllers[event.extra_data['controller_address']].add(address)

        return controllers

    @staticmethod
    def _get_token_balance(
            token: 'EvmToken',
            amount: int,
            token_prices: dict['EvmToken', 'Price'],
    ) -> Balance | None:
        """Return a Balance using the specified amount, token, and prices."""
        if amount == 0 or token not in token_prices:
            return None

        return Balance(
            amount=(normalized_amount := token_normalized_value(
                token_amount=amount,
                token=token,
            )),
            usd_value=normalized_amount * token_prices[token],
        )

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances for Curve lending loans and leveraged positions.
        Funds deposited in lending vaults are represented by cvcrvUSD tokens and
        do not need any special logic here.
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        controllers_with_balances = self._get_controllers_with_balances()
        if len(controllers_with_balances) == 0:
            return balances

        calls: list[tuple[ChecksumEvmAddress, str]] = []
        controller_contract = EvmContract(
            address=ZERO_ADDRESS,  # not used here
            abi=CURVE_VAULT_CONTROLLER_ABI,
            deployed_block=0,  # not used here
        )
        controller_list = []
        user_address_list = []
        for controller_address, user_addresses in controllers_with_balances.items():
            for user_address in user_addresses:
                controller_list.append(controller_address)
                user_address_list.append(user_address)
                calls.append((
                    controller_address,
                    controller_contract.encode(
                        method_name='user_state',
                        arguments=[user_address],
                    ),
                ))

        try:
            call_output = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query Curve lending liabilities due to {e!s}')
            return balances

        unique_tokens = set()
        assets: list[tuple[ChecksumEvmAddress, EvmToken, int]] = []
        liabilities: list[tuple[ChecksumEvmAddress, EvmToken, int]] = []
        for idx, result in enumerate(call_output):
            user_state_data = controller_contract.decode(
                result=result,
                method_name='user_state',
                arguments=[user_address := user_address_list[idx]],
            )[0]
            collateral_amount = user_state_data[0]
            borrowable_collateral_amount = user_state_data[1]
            debt_amount = user_state_data[2]
            if collateral_amount == 0 and borrowable_collateral_amount == 0 and debt_amount == 0:
                continue  # user no longer has balances on this controller

            # Get collateral and borrowed tokens for this controller
            controller_address = controller_list[idx]
            if (tokens := self.get_collateral_and_borrowed_tokens(
                controller_address=controller_address,
                controller_contract=controller_contract,
            )) is None:
                return balances

            collateral_token, borrowed_token = tokens
            if collateral_amount != 0:
                assets.append((user_address, collateral_token, collateral_amount))
                unique_tokens.add(collateral_token)
            if borrowable_collateral_amount != 0:
                assets.append((user_address, borrowed_token, borrowable_collateral_amount))
                unique_tokens.add(borrowed_token)
            if debt_amount != 0:
                liabilities.append((user_address, borrowed_token, debt_amount))
                unique_tokens.add(borrowed_token)

        # Fetch prices for tokens
        token_prices: dict[EvmToken, Price] = {}
        for token in unique_tokens:
            if (price := Inquirer.find_usd_price(asset=token)) == ZERO:
                log.error(f'Failed to query price of {token!s} while fetching Curve lending balances.')  # noqa: E501

            token_prices[token] = price

        # Add assets and liabilities balances
        for user_address, token, amount in assets:
            if (balance := self._get_token_balance(
                    token=token,
                    amount=amount,
                    token_prices=token_prices,
            )):
                balances[user_address].assets[token][self.counterparty] += balance

        for user_address, token, amount in liabilities:
            if (balance := self._get_token_balance(
                    token=token,
                    amount=amount,
                    token_prices=token_prices,
            )):
                balances[user_address].liabilities[token][self.counterparty] += balance

        return balances


class CurveLendBalances(CurveControllerCommonBalances):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
        )

    def get_collateral_and_borrowed_tokens(
            self,
            controller_address: 'ChecksumEvmAddress',
            controller_contract: EvmContract,
    ) -> tuple['EvmToken', 'EvmToken'] | None:
        """Retrieve the collateral and borrowed tokens for the specified controller.
        Both tokens must be retrieved from the controller contract for lend controllers.
        """
        try:
            call_output = self.evm_inquirer.multicall(calls=[
                (controller_address, controller_contract.encode(method_name='collateral_token')),
                (controller_address, controller_contract.encode(method_name='borrowed_token')),
            ])
            return (
                get_or_create_evm_token(
                    userdb=self.evm_inquirer.database,
                    evm_address=deserialize_evm_address(controller_contract.decode(
                        result=call_output[0],
                        method_name='collateral_token',
                    )[0]),
                    chain_id=self.evm_inquirer.chain_id,
                ),
                get_or_create_evm_token(
                    userdb=self.evm_inquirer.database,
                    evm_address=deserialize_evm_address(controller_contract.decode(
                        result=call_output[1],
                        method_name='borrowed_token',
                    )[0]),
                    chain_id=self.evm_inquirer.chain_id,
                ),
            )
        except (RemoteError, DeserializationError, NotERC20Conformant, NotERC721Conformant) as e:
            log.error(
                f'Failed to load tokens for Curve lending controller {controller_address} '
                f'on {self.evm_inquirer.chain_name} due to {e!s}',
            )
            return None
