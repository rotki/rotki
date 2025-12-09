import logging
from collections import defaultdict
from itertools import chain
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_GMX
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, TokenKind
from rotkehlchen.utils.misc import get_chunks

from .constants import CPT_GMX, GMX_READER, GMX_STAKING_REWARD, GMX_USD_DECIMALS, GMX_VAULT_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GmxBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            tx_decoder: 'ArbitrumOneTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_GMX,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.gmx = A_GMX.resolve_to_evm_token()

    def _extract_unique_deposits(self) -> dict['ChecksumEvmAddress', set[tuple[str, str, bool]]]:
        """
        fetch deposit events and remove duplicate positions. Since a user can modify the same
        position increasing or decreasing the collateral we want to remove duplicates to make
        the least amount of queries possible.
        """
        addresses_events = self.addresses_with_activity(
            event_types=self.deposit_event_types,
        )
        unique_deposits = {}
        for address, events in addresses_events.items():
            positions: set[tuple[str, str, bool]] = set()
            for event in events:
                if event.extra_data is None:
                    continue

                try:
                    positions.add((
                        event.extra_data['collateral_token'],
                        event.extra_data['index_token'],
                        event.extra_data['is_long'],
                    ))
                except KeyError as e:
                    log.error(f'GMX event {event} is missing key {e!s}')
                    continue

            unique_deposits[address] = positions
        return unique_deposits

    def query_position_balances(self) -> 'BalancesSheetType':
        """
        Query balances for GMX open positions and returns it.

        The position query uses as argument the address of the user and 3 arrays of collaterals
        used, index tokens used and if the positions are shorts or longs. The arrays must have
        the same length and each index represents a different position inside
        GMX (collaterals[i], index[i], is_long[i]).

        The positions given by the contract are returned using their value in USD and not using
        the amount of tokens in the position. The contract returns the collateral deposit
        (only its USD value) and a delta value that is how much the position has earned
        (also in USD). We sum collateral value + delta to get the current value of the position.

        The total USD value is then converted to the main currency using the current USD price,
        and the token amount is calculated by dividing the USD value by the token's USD price.
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        unique_deposits = self._extract_unique_deposits()
        if len(unique_deposits) == 0:
            return balances

        reader_contract = self.evm_inquirer.contracts.contract(GMX_READER)
        # prepare the arguments for the contract calls and the encoded call
        calls, calls_arguments = [], []
        for address, positions in unique_deposits.items():
            collaterals, itokens, is_long = zip(*chain.from_iterable([position] for position in positions), strict=False)  # noqa: E501
            arguments = [
                GMX_VAULT_ADDRESS,  # vault
                address,  # account
                collaterals,
                itokens,
                is_long,
            ]
            calls_arguments.append(arguments)
            calls.append((
                reader_contract.address,
                reader_contract.encode(
                    method_name='getPositions',
                    arguments=arguments,
                ),
            ))

        if len(calls_arguments) == 0:
            return balances

        try:
            call_output = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query GMX balances due to {e!s}')
            return balances

        main_currency = CachedSettings().main_currency
        for idx, result in enumerate(call_output):  # each iteration is a different address with its positions  # noqa: E501
            pos_information = reader_contract.decode(
                result=result,
                method_name='getPositions',
                arguments=calls_arguments[idx],
            )
            user_address = string_to_evm_address(calls_arguments[idx][1])  # type: ignore[arg-type]  # mypy doesn't detect this as a string
            collaterals_used = calls_arguments[idx][2]
            for position_idx, pos_result in enumerate(get_chunks(pos_information[0], 9)):
                try:  # each position has 9 values returned by gmx
                    collateral_asset = EvmToken(
                        evm_address_to_identifier(
                            address=collaterals_used[position_idx],
                            chain_id=ChainID.ARBITRUM_ONE,
                            token_type=TokenKind.ERC20,
                        ),
                    )
                except (UnknownAsset, WrongAssetType):
                    log.error(
                        f'Arbitrum asset with address {collaterals_used[position_idx]} could '
                        f'not be found during GMX balance query. Skipping.',
                    )
                    continue

                prices = Inquirer.find_prices(
                    from_assets=[collateral_asset, Inquirer.usd],
                    to_asset=main_currency,
                )
                if ZERO in ((asset_price := prices[collateral_asset]), (usd_price := prices[Inquirer.usd])):  # noqa: E501
                    continue

                position_collateral_usd = token_normalized_value_decimals(
                    token_amount=pos_result[1] + pos_result[8],  # sum the collateral + delta (gain or loss)  # noqa: E501
                    token_decimals=GMX_USD_DECIMALS,
                )
                asset_amount = round(
                    number=position_collateral_usd / (asset_price / usd_price),
                    ndigits=collateral_asset.decimals or 18,
                )
                balances[user_address].assets[collateral_asset][self.counterparty] += Balance(
                    amount=asset_amount,
                    value=position_collateral_usd * usd_price,
                )

        return balances

    def query_staking_balances(self, balances: 'BalancesSheetType') -> 'BalancesSheetType':
        """
        Query staked balances for GMX. It modifies the `balances` argument to include
        the staking balances and returns it.
        - This method queries for staked GMX
        - staked GLP (fsGLP) is detected as a token already by the app and price is
        queried correctly
        - sbGMX is also tracked as a token
        - esGMX (vested GMX) is tracked as a token as is not transferable. No price for this asset
        """
        addresses_events = self.addresses_with_activity(
            event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_FOR_WRAPPED)},
        )
        if len(addresses_events) == 0:
            return balances

        reward_contract = self.evm_inquirer.contracts.contract(GMX_STAKING_REWARD)
        gmx_price = Inquirer.find_price(from_asset=A_GMX, to_asset=CachedSettings().main_currency)
        for user_address in addresses_events:
            staked_amount_raw = reward_contract.call(
                node_inquirer=self.evm_inquirer,
                method_name='stakedAmounts',
                arguments=[user_address],
            )
            amount = token_normalized_value_decimals(
                token_amount=staked_amount_raw,
                token_decimals=18,  # GMX has 18 decimals
            )
            balances[user_address].assets[self.gmx][self.counterparty] += Balance(
                amount=amount,
                value=amount * gmx_price,
            )

        return balances

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances for GMX open positions"""
        balances = self.query_position_balances()
        return self.query_staking_balances(balances)
