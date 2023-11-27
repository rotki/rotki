from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.ethereum.constants import RAY_DIGITS
from rotkehlchen.chain.ethereum.defi.defisaver_proxy import HasDSProxy
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_AAVE,
    A_BAL,
    A_BAT,
    A_COMP,
    A_DAI,
    A_ETH,
    A_ETH_MATIC,
    A_GUSD,
    A_KNC,
    A_LINK,
    A_LRC,
    A_MANA,
    A_PAX,
    A_RENBTC,
    A_SAI,
    A_SDAI,
    A_TUSD,
    A_UNI,
    A_USDC,
    A_USDT,
    A_WBTC,
    A_YFI,
    A_ZRX,
)
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int, shift_num_right_by

from .constants import (
    CPT_DSR,
    CPT_MAKERDAO_MIGRATION,
    CPT_SDAI,
    CPT_VAULT,
    MAKERDAO_ICON,
    MAKERDAO_LABEL,
    MAKERDAO_MIGRATION_ADDRESS,
    SDAI_ICON,
    SDAI_LABEL,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


GENERIC_JOIN = b';M\xa6\x9f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501
GENERIC_EXIT = b'\xefi;\xed\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501

POT_JOIN = b'\x04\x98x\xf3\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501
POT_EXIT = b'\x7f\x86a\xa1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501

NEWCDP = b"\xd6\xbe\x0b\xc1xe\x8a8/\xf4\xf9\x1c\x8ch\xb5B\xaakqh[\x8f\xe4'\x96k\x87t\\>\xa7\xa2"
CDPMANAGER_MOVE = b'\xf9\xf3\r\xb6\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501
CDPMANAGER_FROB = b'E\xe6\xbd\xcd\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501

SDAI_DEPOSIT = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
SDAI_REDEEM = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'


class MakerdaoDecoder(DecoderInterface, HasDSProxy):
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        DecoderInterface.__init__(
            self,
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.base = base_tools
        HasDSProxy.__init__(
            self,
            ethereum_inquirer=ethereum_inquirer,
            database=self.base.database,
            premium=None,  # not used here
            msg_aggregator=msg_aggregator,
        )
        self.dai = A_DAI.resolve_to_evm_token()
        self.sai = A_SAI.resolve_to_evm_token()
        self.sdai = A_SDAI.resolve_to_evm_token()
        self.makerdao_cdp_manager = self.ethereum.contracts.contract(string_to_evm_address('0x5ef30b9986345249bc32d8928B7ee64DE9435E39'))  # noqa: E501
        self.makerdao_dai_join = self.ethereum.contracts.contract(string_to_evm_address('0x9759A6Ac90977b93B58547b4A71c78317f391A28'))  # noqa: E501

    def _get_address_or_proxy(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:
        if self.base.is_tracked(address):
            return address

        # not directly from our account. Proxy?
        self.ethereum.proxies_inquirer.get_accounts_having_proxy()
        proxy_owner = self.ethereum.proxies_inquirer.proxy_to_address.get(address)
        if proxy_owner is not None and self.base.is_tracked(proxy_owner):
            return proxy_owner

        return None

    def _get_vault_details(
            self,
            cdp_id: int,
    ) -> tuple[ChecksumEvmAddress, ChecksumEvmAddress]:
        """
        Queries the CDPManager to get the CDP details.
        Returns a tuple with the CDP address and the CDP owner as of the
        time of this call.

        May raise:
        - RemoteError if query to the node failed
        - DeserializationError if the query returns unexpected output
        """
        output = self.ethereum.multicall(
            calls=[(
                self.makerdao_cdp_manager.address,
                self.makerdao_cdp_manager.encode(method_name='urns', arguments=[cdp_id]),
            ), (
                self.makerdao_cdp_manager.address,
                self.makerdao_cdp_manager.encode(method_name='owns', arguments=[cdp_id]),
            )],
        )
        mapping = {}
        for result_encoded, method_name in zip(output, ('urns', 'owns'), strict=True):
            result = self.makerdao_cdp_manager.decode(
                result_encoded,
                method_name,
                arguments=[cdp_id],
            )[0]
            if int(result, 16) == 0:
                raise DeserializationError('Could not deserialize {result} as address}')

            address = deserialize_evm_address(result)
            mapping[method_name] = address

        return mapping['urns'], mapping['owns']

    def decode_makerdao_vault_action(
            self,
            context: DecoderContext,
            vault_asset: CryptoAsset,
            vault_type: str,
    ) -> DecodingOutput:
        if context.tx_log.topics[0] == GENERIC_JOIN:
            raw_amount = hex_or_bytes_to_int(context.tx_log.topics[3])
            amount = asset_normalized_value(
                amount=raw_amount,
                asset=vault_asset,
            )
            # Go through decoded events to find and edit the transfer event
            for event in context.decoded_events:
                if event.event_type == HistoryEventType.SPEND and event.asset == vault_asset and event.balance.amount == amount:  # noqa: E501
                    event.sequence_index = context.tx_log.log_index  # to better position it in the list  # noqa: E501
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = CPT_VAULT
                    event.notes = f'Deposit {amount} {vault_asset.symbol} to {vault_type} MakerDAO vault'  # noqa: E501
                    event.extra_data = {'vault_type': vault_type}
                    return DEFAULT_DECODING_OUTPUT

        elif context.tx_log.topics[0] == GENERIC_EXIT:
            raw_amount = hex_or_bytes_to_int(context.tx_log.topics[3])
            amount = asset_normalized_value(
                amount=raw_amount,
                asset=vault_asset,
            )

            # Go through decoded events to find and edit the transfer event
            for event in context.decoded_events:
                if event.event_type == HistoryEventType.RECEIVE and event.asset == vault_asset and event.balance.amount == amount:  # noqa: E501
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_VAULT
                    event.notes = f'Withdraw {amount} {vault_asset.symbol} from {vault_type} MakerDAO vault'  # noqa: E501
                    event.extra_data = {'vault_type': vault_type}
                    return DEFAULT_DECODING_OUTPUT

        return DEFAULT_DECODING_OUTPUT

    def decode_makerdao_debt_payback(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == GENERIC_JOIN:
            join_user_address = hex_or_bytes_to_address(context.tx_log.topics[2])
            raw_amount = hex_or_bytes_to_int(context.tx_log.topics[3])
            amount = token_normalized_value(
                token_amount=raw_amount,
                token=self.dai,
            )
            # The transfer comes right before, but we don't have enough information
            # yet to make sure that this transfer is indeed a vault payback debt. We
            # need to get a cdp frob event and compare vault id to address matches
            action_item = ActionItem(
                action='transform',
                from_event_type=HistoryEventType.SPEND,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=self.dai,
                amount=amount,
                to_event_subtype=HistoryEventSubType.PAYBACK_DEBT,
                to_counterparty=CPT_VAULT,
                extra_data={'vault_address': join_user_address},
            )
            return DecodingOutput(action_items=[action_item])

        return DEFAULT_DECODING_OUTPUT

    def decode_pot_for_dsr(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == POT_JOIN:
            potjoin_user_address = hex_or_bytes_to_address(context.tx_log.topics[1])
            user = self._get_address_or_proxy(potjoin_user_address)
            if user is None:
                return DEFAULT_DECODING_OUTPUT

            # Now gotta find the DAI join event to get actual DAI value
            daijoin_log = None
            for event_log in context.all_logs:
                if event_log.address == self.makerdao_dai_join.address and event_log.topics[0] == GENERIC_JOIN:  # noqa: E501
                    daijoin_user_address = hex_or_bytes_to_address(event_log.topics[1])
                    if daijoin_user_address != potjoin_user_address:
                        continue  # not a match

                    daijoin_log = event_log
                    break

            if daijoin_log is None:
                return DEFAULT_DECODING_OUTPUT  # no matching daijoin for potjoin

            raw_amount = hex_or_bytes_to_int(daijoin_log.topics[3])
            amount = token_normalized_value(
                token_amount=raw_amount,
                token=self.dai,
            )

            # The transfer event should be right before
            for event in context.decoded_events:
                if event.asset == A_DAI and event.event_type == HistoryEventType.SPEND and event.balance.amount == amount:  # noqa: E501
                    # found the event
                    event.location_label = user
                    event.counterparty = CPT_DSR
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = f'Deposit {amount} DAI in the DSR'
                    return DEFAULT_DECODING_OUTPUT

        elif context.tx_log.topics[0] == POT_EXIT:
            pot_exit_address = hex_or_bytes_to_address(context.tx_log.topics[1])
            user = self._get_address_or_proxy(pot_exit_address)
            if user is None:
                return DEFAULT_DECODING_OUTPUT

            # Now gotta find the DAI exit event to get actual DAI value
            daiexit_log = None
            for event_log in context.all_logs:
                if event_log.address == self.makerdao_dai_join.address and event_log.topics[0] == GENERIC_EXIT:  # noqa: E501
                    daiexit_user_address = hex_or_bytes_to_address(event_log.topics[2])
                    if daiexit_user_address != user:
                        continue  # not a match

                    daiexit_log = event_log
                    break

            if daiexit_log is None:
                return DEFAULT_DECODING_OUTPUT  # no matching daiexit for potexit

            raw_amount = hex_or_bytes_to_int(daiexit_log.topics[3])
            amount = token_normalized_value(
                token_amount=raw_amount,
                token=self.dai,
            )
            # The transfer event will be in a subsequent logs
            action_item = ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=self.dai,
                amount=amount,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
                to_notes=f'Withdraw {amount} DAI from the DSR',
                to_counterparty=CPT_DSR,
            )
            return DecodingOutput(action_items=[action_item])

        return DEFAULT_DECODING_OUTPUT

    def decode_proxy_creation(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == b'%\x9b0\xca9\x88\\m\x80\x1a\x0b]\xbc\x98\x86@\xf3\xc2^/7S\x1f\xe18\xc5\xc5\xaf\x89U\xd4\x1b':  # noqa: E501
            owner_address = hex_or_bytes_to_address(context.tx_log.topics[2])
            if not self.base.is_tracked(owner_address):
                return DEFAULT_DECODING_OUTPUT

            proxy_address = hex_or_bytes_to_address(context.tx_log.data[0:32])
            notes = f'Create DSR proxy {proxy_address} with owner {owner_address}'
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.CREATE,
                asset=A_ETH,
                balance=Balance(),
                location_label=owner_address,
                notes=notes,
                address=proxy_address,
            )
            return DecodingOutput(event=event)

        return DEFAULT_DECODING_OUTPUT

    def _decode_vault_creation(self, context: DecoderContext) -> DecodingOutput:
        owner_address = self._get_address_or_proxy(hex_or_bytes_to_address(context.tx_log.topics[2]))  # noqa: E501
        if owner_address is None:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(owner_address):
            return DEFAULT_DECODING_OUTPUT

        cdp_id = hex_or_bytes_to_int(context.tx_log.topics[3])
        notes = f'Create MakerDAO vault with id {cdp_id} and owner {owner_address}'
        self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            location_label=owner_address,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            balance=Balance(),
            notes=notes,
            counterparty=CPT_VAULT,
            address=context.transaction.to_address,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_vault_debt_generation(self, context: DecoderContext) -> DecodingOutput:
        """Decode vault debt generation by parsing a lognote for cdpmanager move"""
        cdp_id = hex_or_bytes_to_int(context.tx_log.topics[2])
        destination = hex_or_bytes_to_address(context.tx_log.topics[3])

        owner = self._get_address_or_proxy(destination)
        if owner is None:
            return DEFAULT_DECODING_OUTPUT

        # now we need to get the rad and since it's the 3rd argument its not in the indexed topics
        # but it's part of the data location after the first 132 bytes.
        # also need to shift by ray since it's in rad
        raw_amount = shift_num_right_by(hex_or_bytes_to_int(context.tx_log.data[132:164]), RAY_DIGITS)  # noqa: E501
        amount = token_normalized_value(
            token_amount=raw_amount,
            token=self.dai,
        )

        # The transfer event appears after the debt generation event, so we need to transform it
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=self.dai,
            amount=amount,
            to_event_type=HistoryEventType.WITHDRAWAL,
            to_event_subtype=HistoryEventSubType.GENERATE_DEBT,
            to_counterparty=CPT_VAULT,
            to_notes=f'Generate {amount} DAI from MakerDAO vault {cdp_id}',
            extra_data={'cdp_id': cdp_id},
        )
        return DecodingOutput(action_items=[action_item])

    def _decode_vault_change(self, context: DecoderContext) -> DecodingOutput:
        """Decode CDPManger Frob (vault change)

        Used to find the vault id of a collateral deposit
        """
        cdp_id = hex_or_bytes_to_int(context.tx_log.topics[2])
        dink = hex_or_bytes_to_int(context.tx_log.topics[3])

        action_item = None
        for item in context.action_items:
            if item.extra_data and 'vault_address' in item.extra_data:
                action_item = item
                break

        if action_item is not None:
            # this concerns a vault debt payback. Checking only if CDP matches since
            # the owner response is at the time of the call and may have changed
            cdp_address, _ = self._get_vault_details(cdp_id)
            if cdp_address != action_item.extra_data['vault_address']:  # type: ignore
                return DEFAULT_DECODING_OUTPUT  # vault address does not match

            # now find the payback transfer and transform it
            for event in context.decoded_events:
                if event.event_type == action_item.from_event_type and event.event_subtype == action_item.from_event_subtype and event.asset == action_item.asset and event.balance.amount == action_item.amount:  # noqa: E501
                    if action_item.to_event_type:
                        event.event_type = action_item.to_event_type
                    if action_item.to_event_subtype:
                        event.event_subtype = action_item.to_event_subtype
                    if action_item.to_counterparty:
                        event.counterparty = action_item.to_counterparty
                    if action_item.extra_data:
                        event.extra_data = action_item.extra_data
                        event.extra_data['cdp_id'] = cdp_id

                    event.notes = f'Payback {event.balance.amount} DAI of debt to makerdao vault {cdp_id}'  # noqa: E501
                    break

        else:  # collateral deposit
            # dink is the raw collateral amount change. Let's use this event to see if
            # there was a deposit event beforehand to append the cdp id
            for event in context.decoded_events:
                try:
                    crypto_asset = event.asset.resolve_to_crypto_asset()
                except (UnknownAsset, WrongAssetType):
                    self.notify_user(event=event, counterparty=CPT_VAULT)
                    continue
                if event.event_type == HistoryEventType.DEPOSIT and event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET and event.counterparty == CPT_VAULT:  # noqa: E501
                    normalized_dink = asset_normalized_value(
                        amount=dink,
                        asset=event.asset.resolve_to_crypto_asset(),
                    )
                    if normalized_dink != event.balance.amount:
                        continue

                    vault_type = event.extra_data.get('vault_type', 'unknown') if event.extra_data else 'unknown'  # noqa: E501
                    event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} to {vault_type} vault {cdp_id}'  # noqa: E501
                    break

        return DEFAULT_DECODING_OUTPUT

    def decode_cdp_manager_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == NEWCDP:
            return self._decode_vault_creation(context)
        if context.tx_log.topics[0] == CDPMANAGER_MOVE:
            return self._decode_vault_debt_generation(context)
        if context.tx_log.topics[0] == CDPMANAGER_FROB:
            return self._decode_vault_change(context)

        return DEFAULT_DECODING_OUTPUT

    def decode_sdai_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == SDAI_DEPOSIT:  # DAI -> SDAI: owner receives sdai
            owner_address = self._get_address_or_proxy(hex_or_bytes_to_address(context.tx_log.topics[2]))  # noqa: E501
            to_address = owner_address
            from_address: ChecksumEvmAddress | None = self.sdai.evm_address
        elif context.tx_log.topics[0] == SDAI_REDEEM:  # SDAI -> DAI: owner deposits sdai
            owner_address = self._get_address_or_proxy(hex_or_bytes_to_address(context.tx_log.topics[3]))  # noqa: E501
            from_address = owner_address
            to_address = self.sdai.evm_address
        else:
            return DEFAULT_DECODING_OUTPUT

        if from_address is None or to_address is None:
            return DEFAULT_DECODING_OUTPUT

        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(context.tx_log.data[32:64]),
            asset=self.sdai,
        )
        if amount == ZERO:
            return DEFAULT_DECODING_OUTPUT

        if owner_address == from_address:
            event_type = HistoryEventType.DEPOSIT
            event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            notes = f'Return {amount} sDAI to sDAI contract'
        else:
            event_type = HistoryEventType.WITHDRAWAL
            event_subtype = HistoryEventSubType.REMOVE_ASSET
            notes = f'Withdraw {amount} sDAI from sDAI contract'

        transfer = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=self.sdai,
            balance=Balance(amount=amount),
            location_label=owner_address,
            notes=notes,
            address=self.sdai.evm_address,
            counterparty=CPT_SDAI,
        )

        for event in context.decoded_events:
            if event.event_subtype == HistoryEventSubType.NONE:
                incoming_event = event.event_type == HistoryEventType.RECEIVE
                event.event_type = HistoryEventType.WITHDRAWAL if incoming_event else HistoryEventType.DEPOSIT  # noqa: E501
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET if incoming_event else HistoryEventSubType.DEPOSIT_ASSET  # noqa: E501
                verb, preposition = ('Withdraw', 'from') if incoming_event else ('Deposit', 'to')
                event.notes = f'{verb} {event.balance.amount} DAI {preposition} sDAI contract'
                event.address = self.sdai.evm_address
                event.counterparty = CPT_SDAI
                deposit_event, receive_event = (transfer, event) if incoming_event else (event, transfer)  # noqa: E501
                maybe_reshuffle_events(
                    ordered_events=[deposit_event, receive_event],
                    events_list=context.decoded_events,
                )
        return DecodingOutput(event=transfer, action_items=[])

    def decode_saidai_migration(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER:
            to_address = hex_or_bytes_to_address(context.tx_log.topics[2])
            if to_address != MAKERDAO_MIGRATION_ADDRESS:
                return DEFAULT_DECODING_OUTPUT

            # sending SAI to migration contract
            transfer = self.base.decode_erc20_721_transfer(
                token=self.sai,
                tx_log=context.tx_log,
                transaction=context.transaction,
            )
            if transfer is None:
                return DEFAULT_DECODING_OUTPUT

            transfer.event_type = HistoryEventType.MIGRATE
            transfer.event_subtype = HistoryEventSubType.SPEND
            transfer.notes = f'Migrate {transfer.balance.amount} SAI to DAI'
            transfer.counterparty = CPT_MAKERDAO_MIGRATION

            # also create action item for the receive transfer
            action_item = ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=self.dai,
                amount=transfer.balance.amount,
                to_event_type=HistoryEventType.MIGRATE,
                to_event_subtype=HistoryEventSubType.RECEIVE,
                to_notes=f'Receive {transfer.balance.amount} DAI from SAI->DAI migration',
                to_counterparty=CPT_MAKERDAO_MIGRATION,
                to_address=MAKERDAO_MIGRATION_ADDRESS,
            )
            return DecodingOutput(
                event=transfer,
                action_items=[action_item],
            )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            string_to_evm_address('0x3D0B1912B66114d4096F48A8CEe3A56C231772cA'): (self.decode_makerdao_vault_action, A_BAT.resolve_to_crypto_asset(), 'BAT-A'),  # noqa: E501
            string_to_evm_address('0x2F0b23f53734252Bda2277357e97e1517d6B042A'): (self.decode_makerdao_vault_action, A_ETH.resolve_to_crypto_asset(), 'ETH-A'),  # noqa: E501
            string_to_evm_address('0x08638eF1A205bE6762A8b935F5da9b700Cf7322c'): (self.decode_makerdao_vault_action, A_ETH.resolve_to_crypto_asset(), 'ETH-B'),  # noqa: E501
            string_to_evm_address('0xF04a5cC80B1E94C69B48f5ee68a08CD2F09A7c3E'): (self.decode_makerdao_vault_action, A_ETH.resolve_to_crypto_asset(), 'ETH-C'),  # noqa: E501
            string_to_evm_address('0x475F1a89C1ED844A08E8f6C50A00228b5E59E4A9'): (self.decode_makerdao_vault_action, A_KNC.resolve_to_crypto_asset(), 'KNC-A'),  # noqa: E501
            string_to_evm_address('0x4454aF7C8bb9463203b66C816220D41ED7837f44'): (self.decode_makerdao_vault_action, A_TUSD.resolve_to_crypto_asset(), 'TUSD-A'),  # noqa: E501
            string_to_evm_address('0xA191e578a6736167326d05c119CE0c90849E84B7'): (self.decode_makerdao_vault_action, A_USDC.resolve_to_crypto_asset(), 'USDC-A'),  # noqa: E501
            string_to_evm_address('0x2600004fd1585f7270756DDc88aD9cfA10dD0428'): (self.decode_makerdao_vault_action, A_USDC.resolve_to_crypto_asset(), 'USDC-B'),  # noqa: E501
            string_to_evm_address('0x0Ac6A1D74E84C2dF9063bDDc31699FF2a2BB22A2'): (self.decode_makerdao_vault_action, A_USDT.resolve_to_crypto_asset(), 'USDT-A'),  # noqa: E501
            string_to_evm_address('0xBF72Da2Bd84c5170618Fbe5914B0ECA9638d5eb5'): (self.decode_makerdao_vault_action, A_WBTC.resolve_to_crypto_asset(), 'WBTC-A'),  # noqa: E501
            string_to_evm_address('0xfA8c996e158B80D77FbD0082BB437556A65B96E0'): (self.decode_makerdao_vault_action, A_WBTC.resolve_to_crypto_asset(), 'WBTC-B'),  # noqa: E501
            string_to_evm_address('0x7f62f9592b823331E012D3c5DdF2A7714CfB9de2'): (self.decode_makerdao_vault_action, A_WBTC.resolve_to_crypto_asset(), 'WBTC-C'),  # noqa: E501
            string_to_evm_address('0xc7e8Cd72BDEe38865b4F5615956eF47ce1a7e5D0'): (self.decode_makerdao_vault_action, A_ZRX.resolve_to_crypto_asset(), 'ZRX-A'),  # noqa: E501
            string_to_evm_address('0xA6EA3b9C04b8a38Ff5e224E7c3D6937ca44C0ef9'): (self.decode_makerdao_vault_action, A_MANA.resolve_to_crypto_asset(), 'MANA-A'),  # noqa: E501
            string_to_evm_address('0x7e62B7E279DFC78DEB656E34D6a435cC08a44666'): (self.decode_makerdao_vault_action, A_PAX.resolve_to_crypto_asset(), 'PAXUSD-A'),  # noqa: E501
            string_to_evm_address('0xBEa7cDfB4b49EC154Ae1c0D731E4DC773A3265aA'): (self.decode_makerdao_vault_action, A_COMP.resolve_to_crypto_asset(), 'COMP-A'),  # noqa: E501
            string_to_evm_address('0x6C186404A7A238D3d6027C0299D1822c1cf5d8f1'): (self.decode_makerdao_vault_action, A_LRC.resolve_to_crypto_asset(), 'LRC-A'),  # noqa: E501
            string_to_evm_address('0xdFccAf8fDbD2F4805C174f856a317765B49E4a50'): (self.decode_makerdao_vault_action, A_LINK.resolve_to_crypto_asset(), 'LINK-A'),  # noqa: E501
            string_to_evm_address('0x4a03Aa7fb3973d8f0221B466EefB53D0aC195f55'): (self.decode_makerdao_vault_action, A_BAL.resolve_to_crypto_asset(), 'BAL-A'),  # noqa: E501
            string_to_evm_address('0x3ff33d9162aD47660083D7DC4bC02Fb231c81677'): (self.decode_makerdao_vault_action, A_YFI.resolve_to_crypto_asset(), 'YFI-A'),  # noqa: E501
            string_to_evm_address('0xe29A14bcDeA40d83675aa43B72dF07f649738C8b'): (self.decode_makerdao_vault_action, A_GUSD.resolve_to_crypto_asset(), 'GUSD-A'),  # noqa: E501
            string_to_evm_address('0x3BC3A58b4FC1CbE7e98bB4aB7c99535e8bA9b8F1'): (self.decode_makerdao_vault_action, A_UNI.resolve_to_crypto_asset(), 'UNI-A'),  # noqa: E501
            string_to_evm_address('0xFD5608515A47C37afbA68960c1916b79af9491D0'): (self.decode_makerdao_vault_action, A_RENBTC.resolve_to_crypto_asset(), 'RENBTC-A'),  # noqa: E501
            string_to_evm_address('0x24e459F61cEAa7b1cE70Dbaea938940A7c5aD46e'): (self.decode_makerdao_vault_action, A_AAVE.resolve_to_crypto_asset(), 'AAVE-A'),  # noqa: E501
            string_to_evm_address('0x885f16e177d45fC9e7C87e1DA9fd47A9cfcE8E13'): (self.decode_makerdao_vault_action, A_ETH_MATIC.resolve_to_crypto_asset(), 'MATIC-A'),  # noqa: E501
            string_to_evm_address('0x197E90f9FAD81970bA7976f33CbD77088E5D7cf7'): (self.decode_pot_for_dsr,),  # noqa: E501
            self.makerdao_dai_join.address: (self.decode_makerdao_debt_payback,),
            string_to_evm_address('0xA26e15C895EFc0616177B7c1e7270A4C7D51C997'): (self.decode_proxy_creation,),  # noqa: E501
            string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'): (self.decode_saidai_migration,),  # noqa: E501
            self.makerdao_cdp_manager.address: (self.decode_cdp_manager_events,),
            self.sdai.evm_address: (self.decode_sdai_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(
                identifier=CPT_VAULT,
                label=MAKERDAO_LABEL,
                image=MAKERDAO_ICON,
            ), CounterpartyDetails(
                identifier=CPT_DSR,
                label=MAKERDAO_LABEL,
                image=MAKERDAO_ICON,
            ), CounterpartyDetails(
                identifier=CPT_MAKERDAO_MIGRATION,
                label=MAKERDAO_LABEL,
                image=MAKERDAO_ICON,
            ), CounterpartyDetails(
                identifier=CPT_SDAI,
                label=SDAI_LABEL,
                image=SDAI_ICON,
            ),
        )
