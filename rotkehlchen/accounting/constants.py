from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.types import (
    EventCategory,
    EventCategoryDetails,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS

FREE_PNL_EVENTS_LIMIT = 1000
FREE_REPORTS_LOOKUP_LIMIT = 20

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
        HistoryEventSubType.NONE: EventCategory.INFORMATIONAL,  # verify
        HistoryEventSubType.FEE: EventCategory.FEE,
    }, HistoryEventType.RENEW: {
        HistoryEventSubType.NFT: EventCategory.RENEW,
    }, HistoryEventType.STAKING: {
        HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
        HistoryEventSubType.REWARD: EventCategory.STAKING_REWARD,
        HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
        HistoryEventSubType.BLOCK_PRODUCTION: EventCategory.CREATE_BLOCK,
        HistoryEventSubType.MEV_REWARD: EventCategory.MEV_REWARD,
        HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
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

EVENT_CATEGORY_DETAILS = {
    EventCategory.SEND: {None: EventCategoryDetails(
        label='send',
        icon='mdi-arrow-up',
    )}, EventCategory.RECEIVE: {None: EventCategoryDetails(
        label='receive',
        icon='mdi-arrow-down',
        color='green',
    )}, EventCategory.SWAP_OUT: {None: EventCategoryDetails(
        label='swap',
        icon='mdi-arrow-u-right-bottom',
    )}, EventCategory.SWAP_IN: {None: EventCategoryDetails(
        label='swap',
        icon='mdi-arrow-u-left-top',
        color='green',
    )}, EventCategory.MIGRATE_OUT: {None: EventCategoryDetails(
        label='migrate',
        icon='mdi-arrow-u-right-bottom',
    )}, EventCategory.MIGRATE_IN: {None: EventCategoryDetails(
        label='migrate',
        icon='mdi-arrow-u-left-top',
        color='green',
    )}, EventCategory.APPROVAL: {None: EventCategoryDetails(
        label='approval',
        icon='mdi-lock-open-outline',
    )}, EventCategory.DEPOSIT: {None: EventCategoryDetails(
        label='deposit',
        icon='mdi-arrow-expand-up',
        color='green',
    )}, EventCategory.WITHDRAW: {None: EventCategoryDetails(
        label='withdraw',
        icon='mdi-arrow-expand-down',
    )}, EventCategory.AIRDROP: {None: EventCategoryDetails(
        label='airdrop',
        icon='mdi-airballoon-outline',
    )}, EventCategory.BORROW: {None: EventCategoryDetails(
        label='borrow',
        icon='mdi-hand-coin-outline',
    )}, EventCategory.REPAY: {None: EventCategoryDetails(
        label='repay',
        icon='mdi-history',
    )}, EventCategory.DEPLOY: {None: EventCategoryDetails(
        label='deploy',
        icon='mdi-swap-horizontal',
    )}, EventCategory.DEPLOY_WITH_SPEND: {None: EventCategoryDetails(
        label='deploy with spend',
        icon='mdi-swap-horizontal',
    )}, EventCategory.BRIDGE_DEPOSIT: {None: EventCategoryDetails(
        label='bridge',
        icon='mdi-arrow-expand-up',
        color='red',
    )}, EventCategory.BRIDGE_WITHDRAWAL: {None: EventCategoryDetails(
        label='bridge',
        icon='mdi-arrow-expand-down',
        color='green',
    )}, EventCategory.GOVERNANCE: {None: EventCategoryDetails(
        label='governance',
        icon='mdi-bank',
    )}, EventCategory.DONATE: {None: EventCategoryDetails(
        label='donate',
        icon='mdi-hand-heart-outline',
    )}, EventCategory.RECEIVE_DONATION: {None: EventCategoryDetails(
        label='receive donation',
        icon='mdi-hand-heart-outline',
    )}, EventCategory.RENEW: {None: EventCategoryDetails(
        label='renew',
        icon='mdi-calendar-refresh',
    )}, EventCategory.PLACE_ORDER: {None: EventCategoryDetails(
        label='place order',
        icon='mdi-briefcase-arrow-up-down',
    )}, EventCategory.TRANSFER: {None: EventCategoryDetails(
        label='transfer',
        icon='mdi-swap-horizontal',
    )}, EventCategory.STAKING_REWARD: {None: EventCategoryDetails(
        label='staking reward',
        icon='mdi-treasure-chest',
    )}, EventCategory.CLAIM_REWARD: {None: EventCategoryDetails(
        label='claim reward',
        icon='mdi-gift',
    )}, EventCategory.LIQUIDATION_REWARD: {None: EventCategoryDetails(
        label='liquidation reward',
        icon='mdi-water',
    )}, EventCategory.LIQUIDATION_LOSS: {None: EventCategoryDetails(
        label='liquidation loss',
        icon='mdi-water',
    )}, EventCategory.INFORMATIONAL: {None: EventCategoryDetails(
        label='informational',
        icon='mdi-information-outline',
    )}, EventCategory.CANCEL_ORDER: {None: EventCategoryDetails(
        label='cancel order',
        icon='mdi-close-circle-multiple-outline',
        color='red',
    )}, EventCategory.REFUND: {None: EventCategoryDetails(
        label='refund',
        icon='mdi-cash-refund',
    )}, EventCategory.FEE: {
        None: EventCategoryDetails(label='fee', icon='mdi-account-cash'),
        CPT_GAS: EventCategoryDetails(label='gas fee', icon='mdi-fire'),
    }, EventCategory.MEV_REWARD: {None: EventCategoryDetails(
        label='mev',
        icon='mdi-star-box',
    )}, EventCategory.CREATE_BLOCK: {None: EventCategoryDetails(
        label='new block',
        icon='mdi-cube-outline',
    )}, EventCategory.CREATE_PROJECT: {None: EventCategoryDetails(
        label='new project',
        icon='mdi-clipboard-check-outline',
    )}, EventCategory.UPDATE_PROJECT: {None: EventCategoryDetails(
        label='update project',
        icon='mdi-clipboard-plus-outline',
    )}, EventCategory.APPLY: {None: EventCategoryDetails(
        label='apply',
        icon='mdi-application-export',
    )},
}

ACCOUNTING_EVENTS_ICONS = {
    AccountingEventType.TRADE: 'mdi-shuffle-variant',
    AccountingEventType.FEE: 'mdi-account-cash',
    AccountingEventType.ASSET_MOVEMENT: 'mdi-bank-transfer',
    AccountingEventType.MARGIN_POSITION: 'mdi-margin',
    AccountingEventType.LOAN: 'mdi-handshake',
    AccountingEventType.PREFORK_ACQUISITION: 'mdi-source-fork',
    AccountingEventType.STAKING: 'mdi-sprout',
    AccountingEventType.HISTORY_EVENT: 'mdi-history',
    AccountingEventType.TRANSACTION_EVENT: 'mdi-swap-horizontal',
}
