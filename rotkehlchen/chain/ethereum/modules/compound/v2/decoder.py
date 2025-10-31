import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.modules.compound.constants import (
    COMPTROLLER_PROXY_ADDRESS,
    CPT_COMPOUND,
)
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.chain.evm.constants import MINT_TOPIC
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_COMP, A_ETH
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTransaction, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

from .utils import get_compound_underlying_token

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAXIMILLION_ADDR = string_to_evm_address('0xf859A1AD94BcF445A406B892eF0d3082f4174088')
REDEEM_COMPOUND_TOKEN = b'\xe5\xb7T\xfb\x1a\xbb\x7f\x01\xb4\x99y\x1d\x0b\x82\n\xe3\xb6\xaf4$\xac\x1cYv\x8e\xdbS\xf4\xec1\xa9)'  # noqa: E501
BORROW_COMPOUND = b'\x13\xedhf\xd4\xe1\xeem\xa4o\x84\\F\xd7\xe5A \x88=u\xc5\xea\x9a-\xac\xc1\xc4\xca\x89\x84\xab\x80'  # noqa: E501
REPAY_COMPOUND = b'\x1a*"\xcb\x03M&\xd1\x85K\xdcff\xa5\xb9\x1f\xe2^\xfb\xbb]\xca\xd3\xb05Tx\xd6\xf5\xc3b\xa1'  # noqa: E501
LIQUIDATE_BORROW = b')\x867\xf6\x84\xdapgO&P\x9b\x10\xf0~\xc2\xfb\xc7z3Z\xb1\xe7\xd6!ZK$\x84\xd8\xbbR'  # noqa: E501
DISTRIBUTED_SUPPLIER_COMP = b',\xae\xcd\x17\xd0/V\xfa\x89w\x05\xdc\xc7@\xda-#|7?phoN\r\x9b\xd3\xbf\x04\x00\xeaz'  # noqa: E501
DISTRIBUTED_BORROWER_COMP = b'\x1f\xc3\xec\xc0\x87\xd8\xd2\xd1^#\xd0\x03*\xf5\xa4pY\xc3\x89-\x00=\x8e\x13\x9f\xdc\xb6\xbb2|\x99\xa6'  # noqa: E501


class Compoundv2Decoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.ceth = EvmToken('eip155:1/erc20:0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5')

    def _decode_mint(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
            compound_token: EvmToken,
    ) -> EvmDecodingOutput:
        minter = bytes_to_address(tx_log.data[0:32])
        if not self.base.is_tracked(minter):
            return DEFAULT_EVM_DECODING_OUTPUT

        mint_amount_raw = int.from_bytes(tx_log.data[32:64])
        minted_amount_raw = int.from_bytes(tx_log.data[64:96])
        underlying_asset = get_compound_underlying_token(compound_token)
        if underlying_asset is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        mint_amount = asset_normalized_value(mint_amount_raw, underlying_asset)
        minted_amount = token_normalized_value(minted_amount_raw, compound_token)
        out_event = None
        for event in decoded_events:
            # Find the transfer event which should have come before the minting
            if (
                event.event_type == HistoryEventType.SPEND and
                event.asset == underlying_asset and
                event.amount == mint_amount and
                event.address == compound_token.evm_address
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_COMPOUND
                event.notes = f'Deposit {mint_amount} {underlying_asset.symbol} to compound'
                out_event = event
                break

        if out_event is None:
            log.debug(f'At compound mint decoding of tx {transaction.tx_hash!s} the out event was not found')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        # also create an action item for the receive of the cTokens
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=compound_token,
            amount=minted_amount,
            to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            to_notes=f'Receive {minted_amount} {compound_token.symbol} from compound',
            to_counterparty=CPT_COMPOUND,
            paired_events_data=((out_event,), True),
        )
        return EvmDecodingOutput(action_items=[action_item])

    def _decode_redeem(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
            compound_token: EvmToken,
    ) -> EvmDecodingOutput:
        redeemer = bytes_to_address(tx_log.data[0:32])
        if not self.base.is_tracked(redeemer):
            return DEFAULT_EVM_DECODING_OUTPUT

        redeem_amount_raw = int.from_bytes(tx_log.data[32:64])
        redeem_tokens_raw = int.from_bytes(tx_log.data[64:96])
        underlying_asset = get_compound_underlying_token(compound_token)
        if underlying_asset is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        redeem_amount = asset_normalized_value(redeem_amount_raw, underlying_asset)
        redeem_tokens = token_normalized_value(redeem_tokens_raw, compound_token)
        out_event = in_event = None
        for event in decoded_events:
            # Find the transfer event which should have come before the redeeming
            if event.event_type == HistoryEventType.RECEIVE and event.asset == underlying_asset and event.amount == redeem_amount:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_COMPOUND
                event.notes = f'Withdraw {redeem_amount} {underlying_asset.symbol} from compound'
                in_event = event
            if event.event_type == HistoryEventType.SPEND and event.asset == compound_token and event.amount == redeem_tokens:  # noqa: E501
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_COMPOUND
                event.notes = f'Return {redeem_tokens} {compound_token.symbol} to compound'
                out_event = event

        maybe_reshuffle_events(ordered_events=[out_event, in_event], events_list=decoded_events)
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_borrow_and_repay(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
            compound_token: EvmToken,
    ) -> EvmDecodingOutput:
        """
        Decode borrow and repayments for compound tokens
        """
        underlying_token_symbol = compound_token.symbol[1:]
        underlying_asset: CryptoAsset | None

        if underlying_token_symbol == self.eth.symbol:
            underlying_asset = self.eth
        else:
            underlying_asset = get_compound_underlying_token(compound_token)
            if underlying_asset is None:
                return DEFAULT_EVM_DECODING_OUTPUT

        if tx_log.topics[0] == BORROW_COMPOUND:
            amount_raw = int.from_bytes(tx_log.data[32:64])
            payer = None
        else:
            # is a repayment
            amount_raw = int.from_bytes(tx_log.data[64:96])
            payer = bytes_to_address(tx_log.data[0:32])

        amount = asset_normalized_value(amount_raw, underlying_asset)
        for event in decoded_events:
            # Find the transfer event which should have come before the redeeming
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.asset.identifier == underlying_asset and
                event.amount == amount and
                event.address == compound_token.evm_address
            ):
                event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                event.counterparty = CPT_COMPOUND
                event.notes = f'Borrow {amount} {underlying_asset.symbol} from compound'
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == payer and
                event.asset == A_COMP and
                event.address == COMPTROLLER_PROXY_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_COMPOUND
                event.notes = f'Collect {event.amount} COMP from compound'
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.amount == amount and
                (
                    (underlying_asset == self.eth and event.address == MAXIMILLION_ADDR) or
                    (event.location_label == payer and event.address == compound_token.evm_address)
                )
            ):
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.counterparty = CPT_COMPOUND
                event.notes = f'Repay {amount} {underlying_asset.symbol} to compound'

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_liquidate(
            self,
            transaction: EvmTransaction,
            tx_log: 'EvmTxReceiptLog',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> EvmDecodingOutput:
        """Decode a liquidation event happening over a tracked account"""
        borrower = bytes_to_address(tx_log.data[32:64])
        liquidator_address = bytes_to_address(tx_log.data[0:32])
        repay_amount_raw = int.from_bytes(tx_log.data[64:96])
        collateral_ctoken_address = bytes_to_address(tx_log.data[96:128])
        seize_amount_raw = int.from_bytes(tx_log.data[128:160])

        collateral_ctoken = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=collateral_ctoken_address,
            chain_id=self.base.evm_inquirer.chain_id,
            token_kind=TokenKind.ERC20,
            evm_inquirer=self.base.evm_inquirer,
            protocol=CPT_COMPOUND,
        )
        seized_collateral_amount = asset_normalized_value(
            amount=seize_amount_raw,
            asset=collateral_ctoken,
        )
        # use the logs to know what token was getting repaid for the position. We have the ctoken
        # from the event log but not the underlying token. In the case of ETH we need to check if
        # the value sent covers the repaid amount and the token is cETH.
        repaying_asset = None
        if (
            transaction.value >= repay_amount_raw and
            self.ceth.evm_address == tx_log.address
        ):
            repaying_asset = self.eth
        else:
            for event_log in all_logs:
                if (
                    event_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    event_log.topics[1] == tx_log.data[0:32] and
                    bytes_to_address(event_log.topics[2]) == tx_log.address
                ):
                    repaying_token_address = event_log.address
                    repaying_asset = get_or_create_evm_token(
                        userdb=self.base.database,
                        evm_address=repaying_token_address,
                        chain_id=self.base.evm_inquirer.chain_id,
                        token_kind=TokenKind.ERC20,
                        evm_inquirer=self.base.evm_inquirer,
                    )
                    break

        if repaying_asset is None:
            log.error(f'Failed to decode compound liquidation at {transaction.tx_hash!s}')
            return DEFAULT_EVM_DECODING_OUTPUT

        repaid_amount = asset_normalized_value(
            amount=repay_amount_raw,
            asset=repaying_asset,
        )
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == borrower and
                event.address == liquidator_address and
                event.amount == seized_collateral_amount and
                event.asset == collateral_ctoken
            ):
                event.event_type = HistoryEventType.LOSS
                event.event_subtype = HistoryEventSubType.LIQUIDATE
                event.notes = f'Lost {seized_collateral_amount} {collateral_ctoken.symbol} in a compound forced liquidation to repay {repaid_amount} {repaying_asset.symbol}'  # noqa: E501
                event.counterparty = CPT_COMPOUND
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.PAYBACK_DEBT and
                event.location_label == liquidator_address and
                event.amount == repaid_amount and
                event.asset == repaying_asset and
                event.counterparty == CPT_COMPOUND
            ):
                event.notes = f'Repay {repaid_amount} {repaying_asset.symbol} in a compound liquidation'  # noqa: E501
                event.extra_data = {'in_liquidation': True}
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == liquidator_address and
                event.amount == seized_collateral_amount and
                event.asset == collateral_ctoken
            ):
                event.event_subtype = HistoryEventSubType.LIQUIDATE
                event.notes = f'Collect {seized_collateral_amount} {collateral_ctoken.symbol} for performing a compound liquidation'  # noqa: E501
                event.counterparty = CPT_COMPOUND

        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_compound_token_movement(
            self,
            context: DecoderContext,
            compound_token: EvmToken,
    ) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == MINT_TOPIC:
            return self._decode_mint(transaction=context.transaction, tx_log=context.tx_log, decoded_events=context.decoded_events, compound_token=compound_token)  # noqa: E501

        if context.tx_log.topics[0] in (BORROW_COMPOUND, REPAY_COMPOUND):
            return self._decode_borrow_and_repay(tx_log=context.tx_log, decoded_events=context.decoded_events, compound_token=compound_token)  # noqa: E501

        if context.tx_log.topics[0] == REDEEM_COMPOUND_TOKEN:
            return self._decode_redeem(tx_log=context.tx_log, decoded_events=context.decoded_events, compound_token=compound_token)  # noqa: E501

        if context.tx_log.topics[0] == LIQUIDATE_BORROW:
            return self._decode_liquidate(
                transaction=context.transaction,
                tx_log=context.tx_log,
                decoded_events=context.decoded_events,
                all_logs=context.all_logs,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_comp_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        """Example tx:
        https://etherscan.io/tx/0x024bd402420c3ba2f95b875f55ce2a762338d2a14dac4887b78174254c9ab807
        https://etherscan.io/tx/0x25d341421044fa27006c0ec8df11067d80f69b2d2135065828f1992fa6868a49

        A Distributed[Supplier/Borrower]Comp event can happen without a transfer. Just accrues
        comp in the Comptroller until enough for a transfer is there. Also a transfer may
        not happen if comptroller does not have enough comp at the time. And next
        time any such event happens even if compdelta is 0 a big transfer can happen.
        For example check the 2nd transaction has above.

        So the solution for an approach is to count any COMP transfer to the user from
        the comptroller as a reward so long as at least 1 such event exists in the transaction.

        contract code: https://etherscan.io/address/0xBafE01ff935C7305907c33BF824352eE5979B526#code
        """
        if context.tx_log.topics[0] not in (DISTRIBUTED_SUPPLIER_COMP, DISTRIBUTED_BORROWER_COMP):
            return DEFAULT_EVM_DECODING_OUTPUT

        # Transactions with comp claim have many such "distributed" events. We need to do a
        # decoded evens iteration only at the end but can't think of a good way to avoid
        # the possibility of checking all such events
        supplier_address = bytes_to_address(context.tx_log.topics[2])
        if not self.base.is_tracked(supplier_address):
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.location_label == supplier_address and event.asset == A_COMP and event.address == COMPTROLLER_PROXY_ADDRESS:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_COMPOUND
                event.notes = f'Collect {event.amount} COMP from compound'
                break

        else:  # not found, so transfer may come after
            action_item = ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=A_COMP,
                to_event_subtype=HistoryEventSubType.REWARD,
                to_notes='Collect {amount} COMP from compound',  # amount set at actionitem process
                to_counterparty=CPT_COMPOUND,
            )
            return EvmDecodingOutput(action_items=[action_item])

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        compound_tokens = GlobalDBHandler.get_evm_tokens(
            chain_id=ChainID.ETHEREUM,
            protocol='compound',
        )
        mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = {}
        for token in compound_tokens:
            if token == A_COMP:
                continue

            mapping[token.evm_address] = (self.decode_compound_token_movement, token)
        mapping[COMPTROLLER_PROXY_ADDRESS] = (self.decode_comp_claim,)
        return mapping

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_COMPOUND,
            label='Compound',
            image='compound.svg',
        ),)
