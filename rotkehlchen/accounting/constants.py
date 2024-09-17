from typing import Final

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.history.events.structures.types import (
                                                         EventCategory,
                                                         EventCategoryDetails,
                                                         HistoryEventSubType,
                                                         HistoryEventType,
)

FREE_PNL_EVENTS_LIMIT: Final = 1000
FREE_REPORTS_LOOKUP_LIMIT: Final = 20
DEFAULT: Final = 'default'
EXCHANGE: Final = 'exchange'

EVENT_CATEGORY_MAPPINGS = {  # possible combinations of types and subtypes mapped to their event category  # noqa: E501
    HistoryEventType.INFORMATIONAL: {
        HistoryEventSubType.NONE: {DEFAULT: EventCategory.INFORMATIONAL},
        HistoryEventSubType.GOVERNANCE: {DEFAULT: EventCategory.GOVERNANCE},
        HistoryEventSubType.REMOVE_ASSET: {DEFAULT: EventCategory.INFORMATIONAL},
        HistoryEventSubType.PLACE_ORDER: {DEFAULT: EventCategory.PLACE_ORDER},
        HistoryEventSubType.CREATE: {DEFAULT: EventCategory.CREATE_PROJECT},
        HistoryEventSubType.UPDATE: {DEFAULT: EventCategory.UPDATE_PROJECT},
        HistoryEventSubType.APPLY: {DEFAULT: EventCategory.APPLY},
        HistoryEventSubType.APPROVE: {DEFAULT: EventCategory.APPROVAL},
        HistoryEventSubType.ATTEST: {DEFAULT: EventCategory.ATTEST},
    },
    HistoryEventType.RECEIVE: {
        HistoryEventSubType.REWARD: {DEFAULT: EventCategory.CLAIM_REWARD},
        HistoryEventSubType.RECEIVE_WRAPPED: {DEFAULT: EventCategory.RECEIVE},
        HistoryEventSubType.GENERATE_DEBT: {DEFAULT: EventCategory.BORROW},
        HistoryEventSubType.RETURN_WRAPPED: {DEFAULT: EventCategory.RECEIVE},
        HistoryEventSubType.AIRDROP: {DEFAULT: EventCategory.AIRDROP},
        HistoryEventSubType.DONATE: {DEFAULT: EventCategory.RECEIVE_DONATION},
        HistoryEventSubType.NONE: {DEFAULT: EventCategory.RECEIVE},
        HistoryEventSubType.LIQUIDATE: {DEFAULT: EventCategory.LIQUIDATION_REWARD},
        HistoryEventSubType.PAYMENT: {DEFAULT: EventCategory.RECEIVE_PAYMENT},
        HistoryEventSubType.GRANT: {DEFAULT: EventCategory.RECEIVE_GRANT},
        HistoryEventSubType.INTEREST: {DEFAULT: EventCategory.INTEREST},
        HistoryEventSubType.CASHBACK: {DEFAULT: EventCategory.CASHBACK},
    },
    HistoryEventType.DEPOSIT: {
        HistoryEventSubType.DEPOSIT_ASSET: {
            DEFAULT: EventCategory.DEPOSIT,
            EXCHANGE: EventCategory.CEX_DEPOSIT,
        },
        HistoryEventSubType.BRIDGE: {DEFAULT: EventCategory.BRIDGE_DEPOSIT},
        HistoryEventSubType.PLACE_ORDER: {DEFAULT: EventCategory.DEPOSIT},
        HistoryEventSubType.FEE: {DEFAULT: EventCategory.FEE},
    },
    HistoryEventType.SPEND: {
        HistoryEventSubType.RETURN_WRAPPED: {DEFAULT: EventCategory.SEND},
        HistoryEventSubType.PAYBACK_DEBT: {DEFAULT: EventCategory.REPAY},
        HistoryEventSubType.FEE: {DEFAULT: EventCategory.FEE},
        HistoryEventSubType.DONATE: {DEFAULT: EventCategory.DONATE},
        HistoryEventSubType.PAYMENT: {DEFAULT: EventCategory.PAY},
        HistoryEventSubType.NONE: {DEFAULT: EventCategory.SEND},
    },
    HistoryEventType.LOSS: {
        HistoryEventSubType.LIQUIDATE: {DEFAULT: EventCategory.LIQUIDATION_LOSS},
        HistoryEventSubType.HACK: {DEFAULT: EventCategory.HACK_LOSS},
    },
    HistoryEventType.WITHDRAWAL: {
        HistoryEventSubType.REMOVE_ASSET: {
            DEFAULT: EventCategory.WITHDRAW,
            EXCHANGE: EventCategory.CEX_WITHDRAWAL,
        },
        HistoryEventSubType.BRIDGE: {DEFAULT: EventCategory.BRIDGE_WITHDRAWAL},
        HistoryEventSubType.CANCEL_ORDER: {DEFAULT: EventCategory.CANCEL_ORDER},
        HistoryEventSubType.REFUND: {DEFAULT: EventCategory.REFUND},
        HistoryEventSubType.GENERATE_DEBT: {DEFAULT: EventCategory.BORROW},
        HistoryEventSubType.FEE: {DEFAULT: EventCategory.FEE},
    },
    HistoryEventType.TRADE: {
        HistoryEventSubType.SPEND: {DEFAULT: EventCategory.SWAP_OUT},
        HistoryEventSubType.RECEIVE: {DEFAULT: EventCategory.SWAP_IN},
        HistoryEventSubType.NONE: {DEFAULT: EventCategory.INFORMATIONAL},
        HistoryEventSubType.FEE: {DEFAULT: EventCategory.FEE},
    },
    HistoryEventType.RENEW: {
        HistoryEventSubType.NONE: {DEFAULT: EventCategory.RENEW},
    },
    HistoryEventType.STAKING: {
        HistoryEventSubType.DEPOSIT_ASSET: {DEFAULT: EventCategory.STAKE_DEPOSIT},
        HistoryEventSubType.REWARD: {DEFAULT: EventCategory.STAKING_REWARD},
        HistoryEventSubType.REMOVE_ASSET: {DEFAULT: EventCategory.UNSTAKE},
        HistoryEventSubType.BLOCK_PRODUCTION: {DEFAULT: EventCategory.CREATE_BLOCK},
        HistoryEventSubType.MEV_REWARD: {DEFAULT: EventCategory.MEV_REWARD},
        HistoryEventSubType.FEE: {DEFAULT: EventCategory.FEE},
    },
    HistoryEventType.TRANSFER: {
        HistoryEventSubType.DONATE: {DEFAULT: EventCategory.DONATE},
        HistoryEventSubType.NONE: {DEFAULT: EventCategory.TRANSFER},
        HistoryEventSubType.FEE: {DEFAULT: EventCategory.FEE},
    },
    HistoryEventType.ADJUSTMENT: {
        HistoryEventSubType.SPEND: {DEFAULT: EventCategory.SEND},
        HistoryEventSubType.RECEIVE: {DEFAULT: EventCategory.RECEIVE},
    },
    HistoryEventType.DEPLOY: {
        HistoryEventSubType.NONE: {DEFAULT: EventCategory.DEPLOY},
        HistoryEventSubType.SPEND: {DEFAULT: EventCategory.DEPLOY_WITH_SPEND},
        HistoryEventSubType.NFT: {DEFAULT: EventCategory.DEPLOY},
    },
    HistoryEventType.MIGRATE: {
        HistoryEventSubType.SPEND: {DEFAULT: EventCategory.MIGRATE_OUT},
        HistoryEventSubType.RECEIVE: {DEFAULT: EventCategory.MIGRATE_IN},
    },
    HistoryEventType.FAIL: {
        HistoryEventSubType.FEE: {DEFAULT: EventCategory.FAIL},
    },
}

# possible color values
# success=green, error=red, warning=yellow/orangish, info=blue,
# primary=our primary blue color, secondary=somewhat gray
# Icons are taken from here: https://remixicon.com/
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
    )}, EventCategory.CEX_DEPOSIT: {DEFAULT: EventCategoryDetails(
        label='exchange deposit',
        icon='upload-line',
        color='success',
    )}, EventCategory.CEX_WITHDRAWAL: {DEFAULT: EventCategoryDetails(
        label='exchange withdraw',
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
    }, EventCategory.FAIL: {DEFAULT: EventCategoryDetails(
        label='Failed',
        icon='close-circle-line',
        color='error',
    )}, EventCategory.MEV_REWARD: {DEFAULT: EventCategoryDetails(
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
        icon='archive-stack-add-line',
    )}, EventCategory.UNSTAKE: {DEFAULT: EventCategoryDetails(
        label='Unstake',
        icon='archive-stack-reduce-line',
    )}, EventCategory.STAKE_EXIT: {DEFAULT: EventCategoryDetails(
        label='exit',
        icon='archive-stack-reduce-line',
    )}, EventCategory.ATTEST: {DEFAULT: EventCategoryDetails(
        label='Attest',
        icon='quill-pen-line',
    )}, EventCategory.PAY: {DEFAULT: EventCategoryDetails(
        label='pay',
        icon='upload-line',
    )}, EventCategory.RECEIVE_PAYMENT: {DEFAULT: EventCategoryDetails(
        label='receive payment',
        icon='download-line',
    )}, EventCategory.RECEIVE_GRANT: {DEFAULT: EventCategoryDetails(
        label='receive grant',
        icon='hand-coin-line',
    )}, EventCategory.INTEREST: {DEFAULT: EventCategoryDetails(
        label='receive interest',
        icon='funds-line',
    )}, EventCategory.CASHBACK: {DEFAULT: EventCategoryDetails(
        label='Cashback',
        icon='exchange-dollar-line',
    )}, EventCategory.HACK_LOSS: {DEFAULT: EventCategoryDetails(
        label='Hack',
        icon='skull-line',
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
