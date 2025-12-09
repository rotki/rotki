import logging
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, TokenKind

from .constants import CPT_COMPOUND_V3

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CompoundArguments(NamedTuple):
    """Arguments for the multicall to Compound v3 contract function"""
    user_address: ChecksumEvmAddress
    compound_asset: EvmToken


class Compoundv3Balances(ProtocolWithBalance):
    """
    It seems that for compound there is the various COMET contracts
    which are the proxies to which the user supplies collateral. We
    have those marked with compound-v3 protocol in the global DB.

    The underlying token of the cometContract is what is primarily borrowed
    from it. For example for:
    https://basescan.org/address/0xb125e6687d4313864e53df431d5425969c15eb2f#readProxyContract
    it's USDC.

    If you supply USDC to it you can get the balance of your supplied collateral by
    balanceOf on that contract. If you borrow USDC you can get it from borrowBalanceOf
    on that contract.

    But you can also supply other types of collateral to this contract. And to see those
    the user needs to call `userCollateral` on that contract with user address and
    collateral address as arguments.
    """

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_COMPOUND_V3,
            deposit_event_types=set(),
        )

    def _extract_unique_collateral_tokens(self) -> dict[ChecksumEvmAddress, set[CompoundArguments]]:  # noqa: E501
        """Fetch the unique collateral tokens we need to query the comet contracts for"""
        unique_collaterals: dict[ChecksumEvmAddress, set[CompoundArguments]] = defaultdict(set)
        for user_address, events in self.addresses_with_activity(
            event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        ).items():
            for event in events:
                if event.address is None:
                    continue

                if event.asset == self.evm_inquirer.native_token:
                    compound_token = self.evm_inquirer.wrapped_native_token
                else:
                    try:
                        compound_token = event.asset.resolve_to_evm_token()
                    except (UnknownAsset, WrongAssetType):
                        log.warning(
                            'Skipping compound v3 supply event during balance query since '
                            'the asset is not an EVM token so not needed in COMET query',
                        )
                        continue

                unique_collaterals[event.address].add(
                    CompoundArguments(
                        user_address=user_address,
                        compound_asset=EvmToken(evm_address_to_identifier(
                            address=compound_token.evm_address,
                            chain_id=self.evm_inquirer.chain_id,
                            token_type=TokenKind.ERC20,
                        )),
                    ),
                )

        return unique_collaterals

    def _extract_unique_borrowed_tokens(self) -> tuple[dict['EvmToken', set['ChecksumEvmAddress']], dict['ChecksumEvmAddress', 'EvmToken']]:  # noqa: E501
        """
        Fetch unique borrow events from the userDB. Since a user can increase or decrease the same
        liability, we remove the duplicates to reduce the amount of queries. Returns a dict of
        compound token's address -> set of addresses which borrowed the underlying token, and a
        dict of compound token's address -> its underlying token.
        """
        unique_borrows: dict[EvmToken, set[ChecksumEvmAddress]] = defaultdict(set)
        underlying_tokens: dict[ChecksumEvmAddress, EvmToken] = {}
        for address, events in self.addresses_with_activity(
            event_types={(HistoryEventType.RECEIVE, HistoryEventSubType.GENERATE_DEBT)},
        ).items():
            for event in events:
                if event.address is None:
                    continue

                try:
                    compound_token = EvmToken(evm_address_to_identifier(
                        address=event.address,
                        chain_id=self.evm_inquirer.chain_id,
                        token_type=TokenKind.ERC20,
                    ))
                    if (
                        compound_token.underlying_tokens is None or
                        len(compound_token.underlying_tokens) == 0
                    ):
                        log.error(f'No underlying token found for {compound_token!s}.')
                        continue

                    underlying_token = EvmToken(evm_address_to_identifier(
                        address=compound_token.underlying_tokens[0].address,
                        chain_id=self.evm_inquirer.chain_id,
                        token_type=TokenKind.ERC20,
                    ))
                except (UnknownAsset, WrongAssetType) as e:
                    log.error(
                        "Failed to resolve compound v3 borrow event's token and/or its "
                        f'underlying token in {event.location} {event.tx_ref!s} due to {e!s}. Skipping.',  # noqa: E501
                    )
                    continue

                unique_borrows[compound_token].add(address)
                underlying_tokens[event.address] = underlying_token

        return unique_borrows, underlying_tokens

    def query_collateral(self, balances: BalancesSheetType) -> 'BalancesSheetType':
        """Query for the collateral assets saved in the protocol that are in the
        COMET Contract and not as balanceOf in those contracts.
        """
        unique_collaterals_mapping = self._extract_unique_collateral_tokens()
        if len(unique_collaterals_mapping) == 0:
            return balances

        calls: list[tuple[ChecksumEvmAddress, str]] = []
        calls_arguments: list[CompoundArguments] = []
        comet_contract = EvmContract(
            address=ZERO_ADDRESS,  # not used here
            abi=self.evm_inquirer.contracts.abi('COMPOUND_V3_TOKEN'),
            deployed_block=0,  # not used here
        )
        for comet_address, collateral_args in unique_collaterals_mapping.items():
            for arguments in collateral_args:
                calls_arguments.append(arguments)
                calls.append((
                    comet_address,
                    comet_contract.encode(
                        method_name='userCollateral',
                        arguments=[arguments.user_address, arguments.compound_asset.evm_address],
                    ),
                ))

        try:
            call_output = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query Compound v3 collateral due to {e!s}')
            return balances

        main_currency = CachedSettings().main_currency
        for idx, result in enumerate(call_output):
            raw_amount = comet_contract.decode(
                result=result,
                method_name='userCollateral',
                arguments=[
                    calls_arguments[idx].user_address,
                    calls_arguments[idx].compound_asset.evm_address,
                ],
            )[0]
            if raw_amount <= 0:
                continue

            collateral_asset = calls_arguments[idx].compound_asset
            collateral_balance = token_normalized_value_decimals(
                token_amount=raw_amount,
                token_decimals=collateral_asset.decimals,
            )

            if (asset_price := Inquirer.find_price(collateral_asset, main_currency)) == ZERO:
                log.error(
                    f'Failed to query price of {collateral_asset!s} '
                    'while fetching the collateral balances of Compound v3',
                )
                continue

            balances[calls_arguments[idx].user_address].assets[collateral_asset][self.counterparty] += Balance(  # noqa: E501
                amount=collateral_balance,
                value=collateral_balance * asset_price,
            )

        return balances

    def query_liabilities(self) -> 'BalancesSheetType':
        """
        Query liabilities for Compound v3 open positions and return them.

        It calls the Compound token contracts to get the borrow balances of the addresses and
        tokens whose borrow history events are found in the userDB.
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        unique_borrows, underlying_token = self._extract_unique_borrowed_tokens()
        if len(unique_borrows) == 0:
            return balances

        # prepare the arguments for the contract calls and the encoded call
        calls: list[tuple[ChecksumEvmAddress, str]] = []
        calls_arguments: list[CompoundArguments] = []
        token_contract = EvmContract(
            address=ZERO_ADDRESS,  # not used here
            abi=self.evm_inquirer.contracts.abi('COMPOUND_V3_TOKEN'),
            deployed_block=0,  # not used here
        )
        for compound_asset, user_addresses in unique_borrows.items():
            for user_address in user_addresses:
                calls_arguments.append(CompoundArguments(
                    user_address=user_address,
                    compound_asset=compound_asset,
                ))
                calls.append((
                    compound_asset.evm_address,
                    token_contract.encode(
                        method_name='borrowBalanceOf',
                        arguments=[user_address],
                    ),
                ))

        try:
            call_output = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query Compound v3 liabilities due to {e!s}')
            return balances

        main_currency = CachedSettings().main_currency
        for idx, result in enumerate(call_output):
            raw_amount = token_contract.decode(
                result=result,
                method_name='borrowBalanceOf',
                arguments=[calls_arguments[idx].user_address],
            )[0]
            if raw_amount <= 0:
                continue

            borrow_balance = token_normalized_value_decimals(
                token_amount=raw_amount,
                token_decimals=calls_arguments[idx].compound_asset.decimals,
            )

            # query the current price of the underlying asset
            if (asset_price := Inquirer.find_price(underlying_token[calls[idx][0]], main_currency)) == ZERO:  # noqa: E501
                log.error(
                    f'Failed to query price of {underlying_token[calls[idx][0]]!s} '
                    'while fetching the liability balances of Compound v3',
                )
                continue

            balances[calls_arguments[idx].user_address].liabilities[underlying_token[calls[idx][0]]][self.counterparty] += Balance(  # noqa: E501
                amount=borrow_balance,
                value=borrow_balance * asset_price,
            )

        return balances

    def query_balances(self) -> 'BalancesSheetType':
        balances = self.query_liabilities()
        return self.query_collateral(balances)
