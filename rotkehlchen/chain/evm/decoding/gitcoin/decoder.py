import logging
from abc import ABCMeta
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN, GITCOIN_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import (
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
    hex_or_bytes_to_str,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


VOTED = b'\x00d\xca\xa7?\x1dY\xb6\x9a\xdb\xebeeK\x0f\tSYy\x94\xe4$\x1e\xe2F\x0bV\x0b\x8de\xaa\xa2'  # example: https://etherscan.io/tx/0x71fc406467f342f5801560a326aa29ac424381daf17cc04b5573960425ba605b#eventlog  # noqa: E501
VOTED_WITH_ORIGIN = b'\xbf5\xc00\x17\x8a\x1eg\x8c\x82\x96\xa4\xe5\x08>\x90!\xa2L\x1a\x1d\xef\xa5\xbf\xbd\xfd\xe7K\xce\xcf\xa3v'  # noqa: E501 # example: https://optimistic.etherscan.io/tx/0x08685669305ee26060a5a78ae70065aec76d9e62a35f0837c291fb1232f33601#eventlog
PROJECT_CREATED = b'c\xc9/\x95\x05\xd4 \xbf\xf61\xcb\x9d\xf3;\xe9R\xbd\xc1\x1e!\x18\xda6\xa8P\xb4>k\xccL\xe4\xde'  # noqa: E501
METADATA_UPDATED = b'\xf9,&9\xc2]j"\xc3\x8emk)?t\xa9\xb2$\x91\';\x1d\xbbg\xfc\x12U"&\x96\xbe['
NEW_PROJECT_APPLICATION_3ARGS = b'\xcay&"\x04c%\xe9\xcdN$\xb4\x90\xcb\x00\x0e\xf7*\xce\xa3\xa1R\x84\xef\xc1N\xe7\t0z^\x00'  # noqa: E501
NEW_PROJECT_APPLICATION_2ARGS = b'\xecy?\xe7\x04\xd3@\xd9b\xcd\x02\xd8\x1a\xd5@E\xe7\xce\xeaq:\xcaN1\xc7\xc5\xc4>=\xcb\x19*'  # noqa: E501
FUNDS_DISTRIBUTED = b'z\x0b2\xf6\x04\xa8\xc9C&2(a\x03\x9aD\xb7\xedxbL\xf2 \xba\x8bXj$G\xaf\r\x9c\x9b'  # noqa: E501


class GitcoinV2CommonDecoder(DecoderInterface, metaclass=ABCMeta):
    """This is the gitcoin v2 (allo protocol) common decoder

    Not the same as gitcoin v1, or v1.5 (they have changed contracts many times).

    Each round seems to have their own contract address and we need to be
    adding them as part of the constructor here to create the proper mappings.

    Also the payout strategy address should match the number of round implementations.
    Each payout address is found from the round implementation by querying the
    public variable payoutStrategy()

    TODO: Figure out if this can scale better as finding all contract addresses is error prone
    """

    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            project_registry: 'ChecksumEvmAddress',
            voting_impl_addresses: list['ChecksumEvmAddress'],
            round_impl_addresses: list['ChecksumEvmAddress'],
            payout_strategy_addresses: list['ChecksumEvmAddress'],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.project_registry = project_registry
        self.round_impl_addresses = round_impl_addresses
        self.payout_strategy_addresses = payout_strategy_addresses
        assert len(self.payout_strategy_addresses) == len(self.round_impl_addresses), 'payout should match round number'  # noqa: E501
        self.voting_impl_addresses = voting_impl_addresses
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_vote_action(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == VOTED_WITH_ORIGIN:
            donator = hex_or_bytes_to_address(context.tx_log.data[64:96])
            return self._decode_voted(
                context=context,
                donator=donator,
                receiver_start_idx=96,
                paying_contract_idx=1,
            )
        elif context.tx_log.topics[0] == VOTED:
            donator = hex_or_bytes_to_address(context.tx_log.topics[1])
            return self._decode_voted(
                context=context,
                donator=donator,
                receiver_start_idx=64,
                paying_contract_idx=3,
            )

        return DEFAULT_DECODING_OUTPUT

    def _decode_voted(
            self,
            context: DecoderContext,
            donator: 'ChecksumEvmAddress',
            receiver_start_idx: int,
            paying_contract_idx: int,
    ) -> DecodingOutput:
        receiver = hex_or_bytes_to_address(context.tx_log.data[receiver_start_idx:receiver_start_idx + 32])  # noqa: E501
        donator_tracked = self.base.is_tracked(donator)
        receiver_tracked = self.base.is_tracked(receiver)
        if donator_tracked is False and receiver_tracked is False:
            return DEFAULT_DECODING_OUTPUT

        # there is a discrepancy here between the 2 different Voted events
        paying_contract_address = hex_or_bytes_to_address(context.tx_log.topics[paying_contract_idx])  # noqa: E501
        token_address = hex_or_bytes_to_address(context.tx_log.data[:32])
        if token_address == ZERO_ADDRESS:
            asset = self.eth
        else:
            asset = self.base.get_or_create_evm_token(token_address)
        amount_raw = hex_or_bytes_to_int(context.tx_log.data[32:64])
        amount = asset_normalized_value(amount_raw, asset)

        if donator_tracked:  # with or without receiver tracked we take this
            if receiver_tracked:
                new_type = HistoryEventType.TRANSFER
                expected_type = HistoryEventType.RECEIVE
                verb = 'Transfer'
                expected_address = context.tx_log.address
                expected_location_label = receiver
            else:
                new_type = HistoryEventType.SPEND
                expected_type = HistoryEventType.SPEND
                verb = 'Make'
                expected_address = paying_contract_address
                expected_location_label = donator

            notes = f'{verb} a gitcoin donation of {amount} {asset.symbol} to {receiver}'
            for event in context.decoded_events:
                if event.event_type == expected_type and event.event_subtype == HistoryEventSubType.NONE and event.asset == asset and event.location_label == expected_location_label and event.address == expected_address:  # noqa: E501
                    # this is either the internal transfer to the contract that
                    # should later break up into the transfers, or the internal
                    # transfer to the grant if both are tracked. Replace it
                    event.event_type = new_type
                    event.event_subtype = HistoryEventSubType.DONATE
                    event.counterparty = CPT_GITCOIN
                    event.notes = notes
                    event.address = receiver
                    event.balance = Balance(amount)
                    event.location_label = donator
                    break
            else:  # no event found, so create a new one
                event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=new_type,
                    event_subtype=HistoryEventSubType.DONATE,
                    asset=asset,
                    balance=Balance(amount),
                    location_label=donator,
                    notes=notes,
                    counterparty=CPT_GITCOIN,
                    address=receiver,
                )
                return DecodingOutput(event=event)

        else:  # only receiver tracked
            for event in context.decoded_events:
                if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == asset and event.balance.amount == amount:  # noqa: E501
                    event.event_subtype = HistoryEventSubType.DONATE
                    event.counterparty = CPT_GITCOIN
                    event.notes = f'Receive a gitcoin donation of {amount} {asset.symbol} from {donator}'  # noqa: E501
                    break
            else:
                log.error(
                    f'Could not find a corresponding event for donation to {receiver}'
                    f' in {self.evm_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}',  # noqa: E501
                )

        return DEFAULT_DECODING_OUTPUT

    def _decode_project_action(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == PROJECT_CREATED:
            project_id = hex_or_bytes_to_int(context.tx_log.topics[1])
            owner = hex_or_bytes_to_address(context.tx_log.topics[2])
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.CREATE,
                asset=A_ETH,
                balance=Balance(),
                location_label=context.transaction.from_address,
                notes=f'Create gitcoin project with id {project_id} and owner {owner}',
                counterparty=CPT_GITCOIN,
                address=context.tx_log.address,
            )
            return DecodingOutput(event=event)
        elif context.tx_log.topics[0] == METADATA_UPDATED:
            project_id = hex_or_bytes_to_int(context.tx_log.topics[1])
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.UPDATE,
                asset=A_ETH,
                balance=Balance(),
                location_label=context.transaction.from_address,
                notes=f'Update gitcoin project with id {project_id}',
                counterparty=CPT_GITCOIN,
                address=context.tx_log.address,
            )
            return DecodingOutput(event=event)

        return DEFAULT_DECODING_OUTPUT

    def _decode_round_action(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] not in (NEW_PROJECT_APPLICATION_2ARGS, NEW_PROJECT_APPLICATION_3ARGS):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        application_id = hex_or_bytes_to_str(context.tx_log.topics[1])
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPLY,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Apply to gitcoin round with project application id 0x{application_id}',
            counterparty=CPT_GITCOIN,
            address=context.tx_log.address,
        )
        return DecodingOutput(event=event)

    def _decode_payout_action(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != FUNDS_DISTRIBUTED:
            return DEFAULT_DECODING_OUTPUT

        grantee = hex_or_bytes_to_address(context.tx_log.data[32:64])
        if self.base.is_tracked(grantee) is False:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = hex_or_bytes_to_int(context.tx_log.data[0:32])
        token_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        token = self.base.get_or_create_evm_token(token_address)
        amount = asset_normalized_value(raw_amount, token)

        for event in reversed(context.decoded_events):  # transfer event should be right before
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == token and event.balance.amount == amount and event.location_label == grantee:  # noqa: E501
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                event.notes = f'Receive matching payout of {amount} {token.symbol} for a gitcoin round'  # noqa: E501
                break
        else:
            log.error(
                f'Could not find a corresponding event for round payout to {grantee}'
                f' in {self.evm_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}',  # noqa: E501
            )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        mappings: dict['ChecksumEvmAddress', tuple[Any, ...]] = {
            address: (self._decode_vote_action,) for address in self.voting_impl_addresses
        }
        mappings |= {
            address: (self._decode_round_action,) for address in self.round_impl_addresses
        }
        mappings |= {
            address: (self._decode_payout_action,) for address in self.payout_strategy_addresses
        }
        mappings[self.project_registry] = (self._decode_project_action,)
        return mappings

    def counterparties(self) -> list[CounterpartyDetails]:
        return [GITCOIN_CPT_DETAILS]
