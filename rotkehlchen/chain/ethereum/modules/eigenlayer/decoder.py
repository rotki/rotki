import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import AssetWithSymbol
from rotkehlchen.assets.utils import TokenEncounterInfo
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import (
    BEACON_ETH_STRATEGY,
    CHECKPOINT_CREATED,
    CHECKPOINT_FINALIZED,
    CPT_EIGENLAYER,
    DELAYED_WITHDRAWALS_CLAIMED,
    DELAYED_WITHDRAWALS_CREATED,
    DEPOSIT_TOPIC,
    EIGEN_TOKEN_ID,
    EIGENLAYER_AIRDROP_S1_PHASE1_DISTRIBUTOR,
    EIGENLAYER_AIRDROP_S1_PHASE2_DISTRIBUTOR,
    EIGENLAYER_AIRDROP_S2_DISTRIBUTOR,
    EIGENLAYER_CPT_DETAILS,
    EIGENLAYER_DELEGATION,
    EIGENLAYER_STRATEGY_MANAGER,
    EIGENPOD_DELAYED_WITHDRAWAL_ROUTER,
    EIGENPOD_MANAGER,
    FULL_WITHDRAWAL_REDEEMED,
    OPERATOR_SHARES_DECREASED,
    OPERATOR_SHARES_INCREASED,
    PARTIAL_WITHDRAWAL_REDEEMED,
    POD_DEPLOYED,
    POD_SHARES_UPDATED,
    REWARDS_CLAIMED,
    REWARDS_COORDINATOR,
    STRATEGY_ABI,
    STRATEGY_WITHDRAWAL_COMPLETE_TOPIC,
    VALIDATOR_BALANCE_UPDATED,
    WITHDRAWAL_COMPLETED,
    WITHDRAWAL_QUEUED,
)
from rotkehlchen.chain.ethereum.modules.eigenlayer.utils import get_eigenpods_to_owners_mapping
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.clique.decoder import CliqueAirdropDecoderInterface
from rotkehlchen.chain.evm.decoding.interfaces import ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location
from rotkehlchen.utils.misc import (
    bytes_to_address,
    from_gwei,
    from_wei,
    pairwise,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EigenlayerDecoder(CliqueAirdropDecoderInterface, ReloadableDecoderMixin):
    """
    Some info to remember.

    Operators can forcibly undelegate stakers. Any undelegation, whether initiated by a staker
    or their operator, will also queue a withdrawal. That means that if a user was
    forcibly undelegated then we won't see the event since the transaction won't be queried.

    For users like this they would need to add the transaction hash manually and
    associate it with their address.

    Eigenlayer folks also said we could get them with loq querying of this event.
    /// @notice Emitted when @param staker undelegates from @param operator.
    event StakerUndelegated(address indexed staker, address indexed operator);

    That event is in DelegationManager.
    """

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eigenpod_owner_mapping = get_eigenpods_to_owners_mapping(self.base.database)

    def _decode_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        depositor = bytes_to_address(context.tx_log.data[0:32])
        token_addr = bytes_to_address(context.tx_log.data[32:64])
        token_identifier = ethaddress_to_identifier(address=token_addr)
        strategy = bytes_to_address(context.tx_log.data[64:96])

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.asset == token_identifier and
                event.location_label == depositor
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                asset = event.asset.resolve_to_crypto_asset()
                event.notes = f'Deposit {event.amount} {asset.symbol} in EigenLayer'
                event.extra_data = {'strategy': strategy}
                event.product = EvmProduct.STAKING
                event.counterparty = CPT_EIGENLAYER

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_withdrawal(self, context: DecoderContext) -> EvmDecodingOutput:
        """
        Decode withdrawal from eigenlayer. The transaction only contains a transfer event
        and the unstake event but the unstake event doesn't have information about the asset
        or the amount unstaked.
        """
        depositor = bytes_to_address(context.tx_log.topics[1])
        withdrawer = bytes_to_address(context.tx_log.topics[2])
        depositor_is_tracked = self.base.is_tracked(depositor)
        withdrawer_is_tracked = self.base.is_tracked(withdrawer)

        if depositor_is_tracked is True and withdrawer_is_tracked is True:
            event_type, event_subtype = HistoryEventType.STAKING, HistoryEventSubType.REMOVE_ASSET
            notes = 'Unstake {amount} {symbol} from EigenLayer'
        elif depositor_is_tracked is False and withdrawer_is_tracked is True:  # it is unstake + transfer  # noqa: E501
            event_type, event_subtype = HistoryEventType.RECEIVE, HistoryEventSubType.NONE
            notes = 'Receive {amount} {symbol} from EigenLayer depositor {depositor} unstaking'
        elif depositor_is_tracked is True and withdrawer_is_tracked is False:  # we withdraw to a different address not tracked  # noqa: E501
            notes = 'Send {amount} {symbol} from EigenLayer to {withdrawer} via unstaking'
            event_type, event_subtype = HistoryEventType.SPEND, HistoryEventSubType.NONE
        else:
            log.error(f'Unexpected eigenlayer withdrawal in {context.transaction.tx_hash.hex()}. Skipping')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE:
                event.event_type = event_type
                event.event_subtype = event_subtype
                event.counterparty = CPT_EIGENLAYER
                event.product = EvmProduct.STAKING
                event.notes = notes.format(amount=event.amount, symbol=event.asset.resolve_to_crypto_asset().symbol)  # noqa: E501
                break
        else:
            log.error(f'Could not match eigenlayer withdrawal event in {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            return self._decode_deposit(context)
        elif context.tx_log.topics[0] == STRATEGY_WITHDRAWAL_COMPLETE_TOPIC:
            return self._decode_withdrawal(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_airdrop(self, context: DecoderContext, airdrop_identifier: str, note_suffix: str) -> EvmDecodingOutput:  # noqa: E501
        if not (decode_result := self._decode_claim(context)):
            return DEFAULT_EVM_DECODING_OUTPUT

        claiming_address, claimed_amount = decode_result
        notes = f'Claim {claimed_amount} EIGEN from the Eigenlayer airdrop {note_suffix}'
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == claiming_address and
                event.asset.identifier == EIGEN_TOKEN_ID and
                event.amount == claimed_amount
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_EIGENLAYER
                event.notes = notes
                event.extra_data = {AIRDROP_IDENTIFIER_KEY: airdrop_identifier}
                break
        else:
            log.error(f'Could not match eigenlayer airdrop receive event in {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_eigenpod_manager_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == POD_DEPLOYED:
            return self.decode_eigenpod_creation(context)
        elif context.tx_log.topics[0] == POD_SHARES_UPDATED:
            return self.decode_eigenpod_shares_updated(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_eigenpod_shares_updated(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(owner := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        shares_delta = int.from_bytes(context.tx_log.data[0:32])
        notes = f'{"Restake" if shares_delta > 0 else "Unstake"} {from_wei(shares_delta)} ETH'
        if context.transaction.from_address != owner:
            notes += f' for {owner}'
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=owner,
            notes=notes,
            counterparty=CPT_EIGENLAYER,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def decode_eigenpod_creation(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(owner := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        eigenpod_address = bytes_to_address(context.tx_log.topics[1])
        suffix = f' with owner {owner}' if context.transaction.from_address != owner else ''
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=owner,
            notes=f'Deploy eigenpod {eigenpod_address}{suffix}',
            counterparty=CPT_EIGENLAYER,
            address=context.tx_log.address,
            extra_data={'eigenpod_owner': owner, 'eigenpod_address': eigenpod_address},
        )
        return EvmDecodingOutput(events=[event], reload_decoders={'Eigenlayer'})

    def decode_eigenpod_delayed_withdrawals(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == DELAYED_WITHDRAWALS_CREATED:
            return self.decode_eigenpod_delayed_withdrawals_created(context)
        elif context.tx_log.topics[0] == DELAYED_WITHDRAWALS_CLAIMED:
            return self.decode_eigenpod_delayed_withdrawals_claimed(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_eigenpod_delayed_withdrawals_created(self, context: DecoderContext) -> EvmDecodingOutput:  # noqa: E501
        pod_owner = bytes_to_address(context.tx_log.data[0:32])
        recipient = bytes_to_address(context.tx_log.data[32:64])
        if not self.base.any_tracked([pod_owner, recipient]):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = from_wei(int.from_bytes(context.tx_log.data[64:96]))
        partial_withdrawals_redeemed, full_withdrawals_redeemed = 0, 0
        for log_entry in context.all_logs:
            if log_entry.topics[0] == PARTIAL_WITHDRAWAL_REDEEMED:
                partial_withdrawals_redeemed += 1
            elif log_entry.topics[0] == FULL_WITHDRAWAL_REDEEMED:
                full_withdrawals_redeemed += 1

        notes = f'Start a delayed withdrawal of {amount} ETH from Eigenlayer'
        if partial_withdrawals_redeemed != 0 or full_withdrawals_redeemed != 0:
            notes += f' by processing {partial_withdrawals_redeemed} partial and {full_withdrawals_redeemed} full beaconchain withdrawals'  # noqa: E501
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=pod_owner,
            notes=notes,
            counterparty=CPT_EIGENLAYER,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def decode_eigenpod_delayed_withdrawals_claimed(self, context: DecoderContext) -> EvmDecodingOutput:  # noqa: E501
        if not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.data[0:32])):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = from_wei(int.from_bytes(context.tx_log.data[32:64]))
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset == A_ETH and
                    event.location_label == recipient and
                    event.amount == amount
            ):  # not sure if TRANSFER/NONE is best match here but
                # since withdrawals are already tracked by validator index
                # at this point we need to make it into an event that counts
                # as transfer between accounts to avoid double counting
                event.event_type = HistoryEventType.TRANSFER
                event.event_subtype = HistoryEventSubType.NONE
                event.notes = f'Withdraw {event.amount} ETH from Eigenlayer delayed withdrawals'
                event.counterparty = CPT_EIGENLAYER

        log.error(f'Did not find matching eigenlayer ETH transfer for delayed withdrawal claim in {context.transaction.tx_hash.hex()}. Skipping')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_withdrawal_completed(self, context: DecoderContext) -> EvmDecodingOutput:
        """Processes a withdrawal completed event.

        What we do is try to find the previous withdrawal queued event and
        get the withdrawal information from it. Then set it as processed
        so that balance detection of in-flight tokens is adjusted.

        There is some events for which a token transfer does not have to happen such as:
        https://etherscan.io/tx/0xb1a78588e1e43a44814a3620c93afea0cf289a17986c377b6d8eaa6675a0a62e
        That is because the user has the choice to either withdraw tokens as tokens
        and into their wallet, or as shares and keep them into eigenlayer to redeposit
        to some other operator.
        """
        db_filter = EvmEventFilterQuery.make(
            counterparties=[CPT_EIGENLAYER],
            location=Location.from_chain_id(self.node_inquirer.chain_id),
            to_ts=context.transaction.timestamp,
            event_types=[HistoryEventType.INFORMATIONAL],
            event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
        )
        dbevents = DBHistoryEvents(self.base.database)
        with self.base.database.conn.read_ctx() as cursor:
            events = dbevents.get_history_events_internal(
                cursor=cursor,
                filter_query=db_filter,
            )

        withdrawal_root = '0x' + context.tx_log.data.hex()
        for withdrawal_event in events:  # iterate and find the withdrawal event
            if withdrawal_event.extra_data and withdrawal_event.extra_data.get('withdrawal_root', '') == withdrawal_root and not withdrawal_event.extra_data.get('completed', False):  # noqa: E501
                new_event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.INFORMATIONAL,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=withdrawal_event.asset,
                    amount=ZERO,
                    location_label=context.transaction.from_address,
                    notes=f'Complete eigenlayer withdrawal of {withdrawal_event.asset.resolve_to_asset_with_symbol().symbol}',  # noqa: E501
                    counterparty=CPT_EIGENLAYER,
                    address=context.tx_log.address,
                    extra_data={'matched': True},
                )
                with self.base.database.user_write() as write_cursor:
                    dbevents.edit_event_extra_data(  # set withdrawal event as completed
                        write_cursor=write_cursor,
                        event=withdrawal_event,
                        extra_data=withdrawal_event.extra_data | {'completed': True},
                    )

                for event in context.decoded_events:  # and now match the transfer
                    if (
                            event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and  # noqa: E501
                            event.asset == withdrawal_event.asset and
                            event.address == withdrawal_event.extra_data.get('strategy')  # strategy sends it  # noqa: E501
                    ):  # not checking amount as it can differ due to rebasing in some assets
                        event.event_type = HistoryEventType.WITHDRAWAL
                        event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                        event.counterparty = CPT_EIGENLAYER
                        event.notes = f'Withdraw {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Eigenlayer'  # noqa: E501
                        break

                else:  # could not find the transfer, withdrawn as shares and not tokens
                    # https://github.com/Layr-Labs/eigenlayer-contracts/blob/dc3abf5d2a2689a98993c69e962d5d8b299e3fec/docs/core/DelegationManager.md#completequeuedwithdrawal
                    # https://github.com/Layr-Labs/eigenlayer-contracts/tree/dc3abf5d2a2689a98993c69e962d5d8b299e3fec/docs#completing-a-withdrawal-as-tokens
                    new_event.notes += ' as shares'  # type: ignore  # notes is not none

                break  # completed the finding event logic

        else:  # not found. Perhaps transaction and event not pulled or timing issue. Is rechecked from time to time when doing balance queries.  # noqa: E501
            log.debug(f'When decoding eigenlayer WithdrawalCompleted could not find corresponding Withdrawal queued: {context.transaction.tx_hash.hex()}')  # noqa: E501

            new_event = self.base.make_event_from_transaction(  # so let's just keep minimal info
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ZERO,
                location_label=context.transaction.from_address,
                notes=f'Complete eigenlayer withdrawal {withdrawal_root}',
                counterparty=CPT_EIGENLAYER,
                address=context.tx_log.address,
            )

        return EvmDecodingOutput(events=[new_event])

    def _decode_withdrawal_queued(self, context: DecoderContext) -> EvmDecodingOutput:
        """Creates and adds a queued withdrawal for each withdrawal in the event"""
        contract = self.node_inquirer.contracts.contract(EIGENLAYER_DELEGATION)
        _, log_data = contract.decode_event(tx_log=context.tx_log, event_name='WithdrawalQueued', argument_names=('withdrawalRoot', 'withdrawal'))  # noqa: E501
        if not self.base.any_tracked([staker := log_data[1][0], withdrawer := log_data[1][2]]):
            return DEFAULT_EVM_DECODING_OUTPUT

        location_label = withdrawer if self.base.is_tracked(withdrawer) else staker

        strategies = log_data[1][5]
        shares_entries = log_data[1][6]
        if len(strategies) != len(shares_entries):  # should not happen according to contracts
            log.error(f'When decoding eigenlayer WithdrawalQueued len(strategies) != len(shares) for {context.transaction.tx_hash.hex()}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        suffix = f' for {withdrawer}' if withdrawer != context.transaction.from_address else ''
        underlying_tokens, underlying_amounts = self._get_strategy_token_amount(
            strategies=strategies,
            shares_entries=shares_entries,
        )
        for idx, (underlying_token, underlying_amount) in enumerate(zip(underlying_tokens, underlying_amounts, strict=False)):  # noqa: E501
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                asset=underlying_token,
                amount=ZERO,
                location_label=location_label,
                notes=f'Queue withdrawal of {underlying_amount} {underlying_token.symbol} from Eigenlayer{suffix}',  # noqa: E501
                counterparty=CPT_EIGENLAYER,
                address=context.tx_log.address,
                extra_data={
                    'amount': str(underlying_amount),
                    'withdrawer': withdrawer,
                    'withdrawal_root': '0x' + log_data[0].hex(),
                    'strategy': strategies[idx],
                },
            )
            context.decoded_events.append(event)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _get_strategy_token_amount(
            self,
            strategies: list[ChecksumEvmAddress],
            shares_entries: list[int],
    ) -> tuple[list[AssetWithSymbol], list[FVal]]:
        """Queries the chain for the strategy address to get the undlerlying token
        and how much of the undlerying an amount of shares is.

        The given lists have to be the same size
        """
        underlying_tokens: list[AssetWithSymbol] = []
        underlying_amounts, calls = [], []
        beacon_eth_idx = -1
        encounter = TokenEncounterInfo(
            description='Eigenlayer strategy token',
            should_notify=False,
        )
        for idx, (strategy, shares) in enumerate(zip(strategies, shares_entries, strict=False)):
            if strategy == BEACON_ETH_STRATEGY:  # special address, not a contract:
                beacon_eth_idx = idx
                continue

            contract = EvmContract(
                address=strategy,
                abi=STRATEGY_ABI,
                deployed_block=0,  # does not matter
            )
            calls.extend([
                (contract.address, contract.encode(method_name='underlyingToken')),
                (contract.address, contract.encode(method_name='sharesToUnderlyingView', arguments=[shares])),  # noqa: E501

            ])

        output = self.node_inquirer.multicall(calls=calls)
        for raw_address, raw_amount in pairwise(output):
            underlying_tokens.append(underlying_token := self.base.get_or_create_evm_token(
                address=bytes_to_address(raw_address),
                encounter=encounter,
            ))
            underlying_amounts.append(token_normalized_value(
                token_amount=int.from_bytes(raw_amount),
                token=underlying_token,
            ))

        if beacon_eth_idx != -1:  # it's just ETH. Insert at same position
            underlying_tokens.insert(beacon_eth_idx + 1, A_ETH.resolve_to_asset_with_symbol())
            underlying_amounts.insert(beacon_eth_idx + 1, from_wei(shares_entries[beacon_eth_idx]))

        return underlying_tokens, underlying_amounts

    def decode_delegation(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events that delegate shares increase or decrease of an asset to an operator"""
        if context.tx_log.topics[0] == OPERATOR_SHARES_INCREASED:
            verb, preposition = 'Delegate', 'to'
        elif context.tx_log.topics[0] == OPERATOR_SHARES_DECREASED:
            verb, preposition = 'Undelegate', 'from'
        elif context.tx_log.topics[0] == WITHDRAWAL_QUEUED:
            return self. _decode_withdrawal_queued(context)
        elif context.tx_log.topics[0] == WITHDRAWAL_COMPLETED:
            return self. _decode_withdrawal_completed(context)
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(staker := bytes_to_address(context.tx_log.data[0:32])):
            return DEFAULT_EVM_DECODING_OUTPUT

        underlying_tokens, underlying_amounts = self._get_strategy_token_amount(
            strategies=[bytes_to_address(context.tx_log.data[32:64])],
            shares_entries=[int.from_bytes(context.tx_log.data[64:96])],
        )
        operator = bytes_to_address(context.tx_log.topics[1])

        notes = f'{verb} {underlying_amounts[0]} restaked {underlying_tokens[0].symbol} {preposition} {operator}'  # noqa: E501
        if context.transaction.from_address != staker:
            notes += f' for {staker}'
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=underlying_tokens[0],
            amount=ZERO,
            location_label=staker,
            notes=notes,
            counterparty=CPT_EIGENLAYER,
            address=context.tx_log.address,
            extra_data={'amount': str(underlying_amounts[0])},
        )

        return EvmDecodingOutput(events=[event])

    def _decode_start_checkpoint(self, context: DecoderContext) -> EvmDecodingOutput:
        beacon_blockroot = '0x' + context.tx_log.topics[2].hex()
        validators_num = int.from_bytes(context.tx_log.data)
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Start an eigenpod checkpoint of {validators_num} validators at beacon blockroot {beacon_blockroot}',  # noqa: E501
            counterparty=CPT_EIGENLAYER,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_finalize_checkpoint(self, context: DecoderContext) -> EvmDecodingOutput:
        total_shares_delta = from_wei(int.from_bytes(context.tx_log.data))
        if total_shares_delta >= 0:
            action = f'add {total_shares_delta} ETH for'
        else:
            action = f'remove {-total_shares_delta} ETH from'
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Finalize an eigenpod checkpoint and {action} restaking across all validators',
            counterparty=CPT_EIGENLAYER,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_validator_balance_updated(self, context: DecoderContext) -> EvmDecodingOutput:
        validator_index = int.from_bytes(context.tx_log.data[0:32])
        validator_balance = from_gwei(int.from_bytes(context.tx_log.data[64:96]))

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Update validator {validator_index} restaking balance to {validator_balance}',
            counterparty=CPT_EIGENLAYER,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def decode_eigenpod_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == CHECKPOINT_CREATED:
            return self._decode_start_checkpoint(context)
        elif context.tx_log.topics[0] == CHECKPOINT_FINALIZED:
            return self._decode_finalize_checkpoint(context)
        elif context.tx_log.topics[0] == VALIDATOR_BALANCE_UPDATED:
            return self._decode_validator_balance_updated(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_rewards_coordinator(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != REWARDS_CLAIMED:
            return DEFAULT_EVM_DECODING_OUTPUT

        earner = bytes_to_address(context.tx_log.topics[1])
        claimer = bytes_to_address(context.tx_log.topics[2])
        recipient = bytes_to_address(context.tx_log.topics[2])
        if not self.base.any_tracked([earner, claimer, recipient]):
            return DEFAULT_EVM_DECODING_OUTPUT

        token_address = bytes_to_address(context.tx_log.data[32:64])
        token = self.base.get_or_create_evm_token(
            address=token_address,
            encounter=TokenEncounterInfo(
                description='Eigenlayer AVS reward claim',
                should_notify=False,
            ),
        )
        amount_raw = int.from_bytes(context.tx_log.data[64:96])
        amount = token_normalized_value(token_amount=amount_raw, token=token)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == token and event.amount == amount:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_EIGENLAYER
                verb = 'Claim' if self.base.is_tracked(claimer) else 'Receive'
                event.notes = f'{verb} {amount} {token.symbol} as AVS restaking reward'
                break

        else:
            log.error(f'During decoding eigenlayer AVS reward claiming for {context.transaction} could not find the token transfer')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        eigenpod_mappings = dict.fromkeys(self.eigenpod_owner_mapping.keys(), (self.decode_eigenpod_events,))  # noqa: E501
        return eigenpod_mappings | {
            EIGENLAYER_STRATEGY_MANAGER: (self.decode_event,),
            EIGENLAYER_AIRDROP_S1_PHASE1_DISTRIBUTOR: (self.decode_airdrop, 'eigen_s1_phase1', 'season 1 phase 1'),  # noqa: E501
            EIGENLAYER_AIRDROP_S1_PHASE2_DISTRIBUTOR: (self.decode_airdrop, 'eigen_s1_phase2', 'season 1 phase 2'),  # noqa: E501
            EIGENLAYER_AIRDROP_S2_DISTRIBUTOR: (self.decode_airdrop, 'eigen_s2', 'season 2'),
            EIGENPOD_MANAGER: (self.decode_eigenpod_manager_events,),
            EIGENPOD_DELAYED_WITHDRAWAL_ROUTER: (self.decode_eigenpod_delayed_withdrawals,),
            EIGENLAYER_DELEGATION: (self.decode_delegation,),
            REWARDS_COORDINATOR: (self.decode_rewards_coordinator,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (EIGENLAYER_CPT_DETAILS,)

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {CPT_EIGENLAYER: [EvmProduct.STAKING]}

    # -- ReloadableDecoderMixin methods

    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        """Reload the eigenpod owners mapping and return the new addresses to decoders mapping"""
        self.eigenpod_owner_mapping = get_eigenpods_to_owners_mapping(self.base.database)
        return self.addresses_to_decoders()
