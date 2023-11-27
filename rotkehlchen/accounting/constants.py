from typing import Final

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.history.events.structures.types import (
    EventCategory,
    EventCategoryDetails,
    HistoryEventSubType,
    HistoryEventType,
)

FREE_PNL_EVENTS_LIMIT = 1000
FREE_REPORTS_LOOKUP_LIMIT = 20
DEFAULT: Final = 'default'

EVENT_CATEGORY_MAPPINGS = {  # possible combinations of types and subtypes mapped to their event category  # noqa: E501
    HistoryEventType.INFORMATIONAL: {
        HistoryEventSubType.NONE: EventCategory.INFORMATIONAL,
        HistoryEventSubType.GOVERNANCE: EventCategory.GOVERNANCE,
        HistoryEventSubType.REMOVE_ASSET: EventCategory.INFORMATIONAL,
        HistoryEventSubType.PLACE_ORDER: EventCategory.PLACE_ORDER,
        HistoryEventSubType.CREATE: EventCategory.CREATE_PROJECT,
        HistoryEventSubType.UPDATE: EventCategory.UPDATE_PROJECT,
        HistoryEventSubType.APPLY: EventCategory.APPLY,
        HistoryEventSubType.APPROVE: EventCategory.APPROVAL,
        HistoryEventSubType.ATTEST: EventCategory.ATTEST,
    }, HistoryEventType.RECEIVE: {
        HistoryEventSubType.REWARD: EventCategory.CLAIM_REWARD,
        HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
        HistoryEventSubType.GENERATE_DEBT: EventCategory.BORROW,
        HistoryEventSubType.RETURN_WRAPPED: EventCategory.RECEIVE,
        HistoryEventSubType.AIRDROP: EventCategory.AIRDROP,
        HistoryEventSubType.DONATE: EventCategory.RECEIVE_DONATION,
        HistoryEventSubType.NONE: EventCategory.RECEIVE,
        HistoryEventSubType.LIQUIDATE: EventCategory.LIQUIDATION_REWARD,
    }, HistoryEventType.DEPOSIT: {
        HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
        HistoryEventSubType.BRIDGE: EventCategory.BRIDGE_DEPOSIT,
        HistoryEventSubType.PLACE_ORDER: EventCategory.DEPOSIT,
        HistoryEventSubType.FEE: EventCategory.FEE,
    }, HistoryEventType.SPEND: {
        HistoryEventSubType.RETURN_WRAPPED: EventCategory.SEND,
        HistoryEventSubType.LIQUIDATE: EventCategory.LIQUIDATION_LOSS,
        HistoryEventSubType.PAYBACK_DEBT: EventCategory.REPAY,
        HistoryEventSubType.FEE: EventCategory.FEE,
        HistoryEventSubType.DONATE: EventCategory.DONATE,
        HistoryEventSubType.NONE: EventCategory.SEND,
    }, HistoryEventType.WITHDRAWAL: {
        HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
        HistoryEventSubType.BRIDGE: EventCategory.BRIDGE_WITHDRAWAL,
        HistoryEventSubType.CANCEL_ORDER: EventCategory.CANCEL_ORDER,
        HistoryEventSubType.REFUND: EventCategory.REFUND,
        HistoryEventSubType.GENERATE_DEBT: EventCategory.BORROW,
        HistoryEventSubType.FEE: EventCategory.FEE,
    }, HistoryEventType.TRADE: {
        HistoryEventSubType.SPEND: EventCategory.SWAP_OUT,
        HistoryEventSubType.RECEIVE: EventCategory.SWAP_IN,
        HistoryEventSubType.NONE: EventCategory.INFORMATIONAL,
        HistoryEventSubType.FEE: EventCategory.FEE,
    }, HistoryEventType.RENEW: {
        HistoryEventSubType.NONE: EventCategory.RENEW,
    }, HistoryEventType.STAKING: {
        HistoryEventSubType.DEPOSIT_ASSET: EventCategory.STAKE_DEPOSIT,
        HistoryEventSubType.REWARD: EventCategory.STAKING_REWARD,
        HistoryEventSubType.REMOVE_ASSET: EventCategory.STAKE_WITHDRAWAL,
        HistoryEventSubType.BLOCK_PRODUCTION: EventCategory.CREATE_BLOCK,
        HistoryEventSubType.MEV_REWARD: EventCategory.MEV_REWARD,
        HistoryEventSubType.FEE: EventCategory.FEE,
    }, HistoryEventType.TRANSFER: {
        HistoryEventSubType.DONATE: EventCategory.DONATE,
        HistoryEventSubType.NONE: EventCategory.TRANSFER,
    }, HistoryEventType.ADJUSTMENT: {
        HistoryEventSubType.SPEND: EventCategory.SEND,
        HistoryEventSubType.RECEIVE: EventCategory.RECEIVE,
    }, HistoryEventType.DEPLOY: {
        HistoryEventSubType.NONE: EventCategory.DEPLOY,
        HistoryEventSubType.SPEND: EventCategory.DEPLOY_WITH_SPEND,
        HistoryEventSubType.NFT: EventCategory.DEPLOY,
    }, HistoryEventType.MIGRATE: {
        HistoryEventSubType.SPEND: EventCategory.MIGRATE_OUT,
        HistoryEventSubType.RECEIVE: EventCategory.MIGRATE_IN,
    },
}

# possible color values
# success=green, error=red, warning=yellow/orangish, info=blue,
# primary=our primary blue color, secondary=somewhat gray
# IMPORTANT: All icons added here need to also be packaged in the frontend
# here frontend/app/src/plugins/rui/index.ts
EVENT_CATEGORY_DETAILS = {
    EventCategory.SEND: {DEFAULT: EventCategoryDetails(
        label='send',
        icon='arrow-up-line',
    )}, EventCategory.RECEIVE: {DEFAULT: EventCategoryDetails(
        label='receive',
        icon='arrow-down-line',
        color='success',
    )}, EventCategory.SWAP_OUT: {DEFAULT: EventCategoryDetails(
        label='swap',
        icon='arrow-go-forward-line',
    )}, EventCategory.SWAP_IN: {DEFAULT: EventCategoryDetails(
        label='swap',
        icon='arrow-go-back-line',
        color='success',
    )}, EventCategory.MIGRATE_OUT: {DEFAULT: EventCategoryDetails(
        label='migrate',
        icon='arrow-go-forward-line',
    )}, EventCategory.MIGRATE_IN: {DEFAULT: EventCategoryDetails(
        label='migrate',
        icon='arrow-go-back-line',
        color='success',
    )}, EventCategory.APPROVAL: {DEFAULT: EventCategoryDetails(
        label='approval',
        icon='lock-unlock-line',
    )}, EventCategory.DEPOSIT: {DEFAULT: EventCategoryDetails(
        label='deposit',
        icon='upload-line',
        color='success',
    )}, EventCategory.WITHDRAW: {DEFAULT: EventCategoryDetails(
        label='withdraw',
        icon='download-line',
    )}, EventCategory.AIRDROP: {DEFAULT: EventCategoryDetails(
        label='airdrop',
        icon='gift-line',
    )}, EventCategory.BORROW: {DEFAULT: EventCategoryDetails(
        label='borrow',
        icon='hand-coin-line',
    )}, EventCategory.REPAY: {DEFAULT: EventCategoryDetails(
        label='repay',
        icon='history-line',
    )}, EventCategory.DEPLOY: {DEFAULT: EventCategoryDetails(
        label='deploy',
        icon='rocket-line',
    )}, EventCategory.DEPLOY_WITH_SPEND: {DEFAULT: EventCategoryDetails(
        label='deploy with spend',
        icon='rocket-2-line',
    )}, EventCategory.BRIDGE_DEPOSIT: {DEFAULT: EventCategoryDetails(
        label='bridge',
        icon='upload-line',
        color='error',
    )}, EventCategory.BRIDGE_WITHDRAWAL: {DEFAULT: EventCategoryDetails(
        label='bridge',
        icon='download-line',
        color='success',
    )}, EventCategory.GOVERNANCE: {DEFAULT: EventCategoryDetails(
        label='governance',
        icon='government-line',
    )}, EventCategory.DONATE: {DEFAULT: EventCategoryDetails(
        label='donate',
        icon='hand-heart-line',
    )}, EventCategory.RECEIVE_DONATION: {DEFAULT: EventCategoryDetails(
        label='receive donation',
        icon='heart-2-line',
    )}, EventCategory.RENEW: {DEFAULT: EventCategoryDetails(
        label='renew',
        icon='loop-right-line',
    )}, EventCategory.PLACE_ORDER: {DEFAULT: EventCategoryDetails(
        label='place order',
        icon='briefcase-line',
    )}, EventCategory.TRANSFER: {DEFAULT: EventCategoryDetails(
        label='transfer',
        icon='swap-box-line',
    )}, EventCategory.STAKING_REWARD: {DEFAULT: EventCategoryDetails(
        label='staking reward',
        icon='trophy-line',
    )}, EventCategory.CLAIM_REWARD: {DEFAULT: EventCategoryDetails(
        label='claim reward',
        icon='gift-2-line',
    )}, EventCategory.LIQUIDATION_REWARD: {DEFAULT: EventCategoryDetails(
        label='liquidation reward',
        icon='drop-fill',
    )}, EventCategory.LIQUIDATION_LOSS: {DEFAULT: EventCategoryDetails(
        label='liquidation loss',
        icon='contrast-drop-fill',
    )}, EventCategory.INFORMATIONAL: {DEFAULT: EventCategoryDetails(
        label='informational',
        icon='information-line',
    )}, EventCategory.CANCEL_ORDER: {DEFAULT: EventCategoryDetails(
        label='cancel order',
        icon='file-close-line',
        color='error',
    )}, EventCategory.REFUND: {DEFAULT: EventCategoryDetails(
        label='refund',
        icon='refund-2-line',
    )}, EventCategory.FEE: {
        DEFAULT: EventCategoryDetails(label='fee', icon='cash-line'),
        CPT_GAS: EventCategoryDetails(label='gas fee', icon='fire-line'),
    }, EventCategory.MEV_REWARD: {DEFAULT: EventCategoryDetails(
        label='mev',
        icon='medal-line',
    )}, EventCategory.CREATE_BLOCK: {DEFAULT: EventCategoryDetails(
        label='new block',
        icon='box-3-line',
    )}, EventCategory.CREATE_PROJECT: {DEFAULT: EventCategoryDetails(
        label='new project',
        icon='file-add-line',
    )}, EventCategory.UPDATE_PROJECT: {DEFAULT: EventCategoryDetails(
        label='update project',
        icon='file-edit-line',
    )}, EventCategory.APPLY: {DEFAULT: EventCategoryDetails(
        label='apply',
        icon='share-circle-line',
    )}, EventCategory.STAKE_DEPOSIT: {DEFAULT: EventCategoryDetails(
        label='Stake',
        icon='folder-add-line',
    )}, EventCategory.STAKE_WITHDRAWAL: {DEFAULT: EventCategoryDetails(
        label='Unstake',
        icon='folder-reduce-line',
    )}, EventCategory.ATTEST: {DEFAULT: EventCategoryDetails(
        label='Attest',
        icon='quill-pen-line',
    )},
}

ACCOUNTING_EVENTS_ICONS = {
    AccountingEventType.TRADE: 'swap-box-line',
    AccountingEventType.FEE: 'price-tag-line',
    AccountingEventType.ASSET_MOVEMENT: 'token-swap-line',
    AccountingEventType.MARGIN_POSITION: 'percent-line',
    AccountingEventType.LOAN: 'shake-hands-line',
    AccountingEventType.PREFORK_ACQUISITION: 'git-branch-line',
    AccountingEventType.STAKING: 'seedling-line',
    AccountingEventType.HISTORY_EVENT: 'exchange-box-line',
    AccountingEventType.TRANSACTION_EVENT: 'arrow-left-right-line',
}
