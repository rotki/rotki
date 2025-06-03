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
        HistoryEventSubType.DEPOSIT_ASSET: {DEFAULT: EventCategory.INFORMATIONAL},
        HistoryEventSubType.REMOVE_ASSET: {DEFAULT: EventCategory.WITHDRAW},
        HistoryEventSubType.PLACE_ORDER: {DEFAULT: EventCategory.PLACE_ORDER},
        HistoryEventSubType.CREATE: {DEFAULT: EventCategory.CREATE_PROJECT},
        HistoryEventSubType.UPDATE: {DEFAULT: EventCategory.UPDATE},
        HistoryEventSubType.APPLY: {DEFAULT: EventCategory.APPLY},
        HistoryEventSubType.APPROVE: {DEFAULT: EventCategory.APPROVAL},
        HistoryEventSubType.ATTEST: {DEFAULT: EventCategory.ATTEST},
        HistoryEventSubType.MEV_REWARD: {DEFAULT: EventCategory.MEV_REWARD},
        HistoryEventSubType.BLOCK_PRODUCTION: {DEFAULT: EventCategory.CREATE_BLOCK},
        HistoryEventSubType.CONSOLIDATE: {DEFAULT: EventCategory.COMBINE},
        HistoryEventSubType.DELEGATE: {DEFAULT: EventCategory.DELEGATE},
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
        HistoryEventSubType.REFUND: {DEFAULT: EventCategory.REFUND},
    },
    HistoryEventType.DEPOSIT: {
        HistoryEventSubType.DEPOSIT_ASSET: {
            DEFAULT: EventCategory.DEPOSIT,
            EXCHANGE: EventCategory.CEX_DEPOSIT,
        },
        HistoryEventSubType.DEPOSIT_FOR_WRAPPED: {DEFAULT: EventCategory.DEPOSIT},
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
        HistoryEventSubType.CLAWBACK: {DEFAULT: EventCategory.CLAWBACK},
        HistoryEventSubType.BURN: {DEFAULT: EventCategory.BURN},
    },
    HistoryEventType.LOSS: {
        HistoryEventSubType.LIQUIDATE: {DEFAULT: EventCategory.LIQUIDATION_LOSS},
        HistoryEventSubType.HACK: {DEFAULT: EventCategory.HACK_LOSS},
        HistoryEventSubType.LIQUIDITY_PROVISION_LOSS: {DEFAULT: EventCategory.LIQUIDITY_PROVISION_LOSS},  # noqa: E501
        HistoryEventSubType.NONE: {DEFAULT: EventCategory.LOSS},
    },
    HistoryEventType.WITHDRAWAL: {
        HistoryEventSubType.REMOVE_ASSET: {
            DEFAULT: EventCategory.WITHDRAW,
            EXCHANGE: EventCategory.CEX_WITHDRAWAL,
        },
        HistoryEventSubType.REDEEM_WRAPPED: {DEFAULT: EventCategory.WITHDRAW},
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
        HistoryEventSubType.DEPOSIT_FOR_WRAPPED: {DEFAULT: EventCategory.STAKE_DEPOSIT},
        HistoryEventSubType.REWARD: {DEFAULT: EventCategory.STAKING_REWARD},
        HistoryEventSubType.REMOVE_ASSET: {DEFAULT: EventCategory.UNSTAKE},
        HistoryEventSubType.REDEEM_WRAPPED: {DEFAULT: EventCategory.UNSTAKE},
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
    HistoryEventType.MINT: {
        HistoryEventSubType.NFT: {DEFAULT: EventCategory.MINT_NFT},
        HistoryEventSubType.FEE: {DEFAULT: EventCategory.FEE},
    },
    HistoryEventType.BURN: {
        HistoryEventSubType.NFT: {DEFAULT: EventCategory.BURN},
    },
    HistoryEventType.MULTI_TRADE: {
        HistoryEventSubType.SPEND: {DEFAULT: EventCategory.SWAP_OUT},
        HistoryEventSubType.RECEIVE: {DEFAULT: EventCategory.SWAP_IN},
        HistoryEventSubType.FEE: {DEFAULT: EventCategory.FEE},
    },
}

EVENT_GROUPING_ORDER = {  # Determines how to group events when serializing for the api
    HistoryEventType.TRADE: (spend_receive_fee := {
        HistoryEventSubType.SPEND: 0,
        HistoryEventSubType.RECEIVE: 1,
        HistoryEventSubType.FEE: 2,
    }),
    HistoryEventType.MULTI_TRADE: spend_receive_fee,
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
        icon='lu-arrow-up',
    )}, EventCategory.RECEIVE: {DEFAULT: EventCategoryDetails(
        label='receive',
        icon='lu-arrow-down',
        color='success',
    )}, EventCategory.SWAP_OUT: {DEFAULT: EventCategoryDetails(
        label='swap',
        icon='lu-redo-2',
    )}, EventCategory.SWAP_IN: {DEFAULT: EventCategoryDetails(
        label='swap',
        icon='lu-undo-2',
        color='success',
    )}, EventCategory.MIGRATE_OUT: {DEFAULT: EventCategoryDetails(
        label='migrate',
        icon='lu-redo-2',
    )}, EventCategory.MIGRATE_IN: {DEFAULT: EventCategoryDetails(
        label='migrate',
        icon='lu-undo-2',
        color='success',
    )}, EventCategory.APPROVAL: {DEFAULT: EventCategoryDetails(
        label='approval',
        icon='lu-lock-keyhole-open',
    )}, EventCategory.DEPOSIT: {DEFAULT: EventCategoryDetails(
        label='deposit',
        icon='lu-upload',
        color='success',
    )}, EventCategory.WITHDRAW: {DEFAULT: EventCategoryDetails(
        label='withdraw',
        icon='lu-download',
    )}, EventCategory.CEX_DEPOSIT: {DEFAULT: EventCategoryDetails(
        label='exchange deposit',
        icon='lu-upload',
        color='success',
    )}, EventCategory.CEX_WITHDRAWAL: {DEFAULT: EventCategoryDetails(
        label='exchange withdraw',
        icon='lu-download',
    )}, EventCategory.AIRDROP: {DEFAULT: EventCategoryDetails(
        label='airdrop',
        icon='lu-gift',
    )}, EventCategory.BORROW: {DEFAULT: EventCategoryDetails(
        label='borrow',
        icon='lu-hand-coins',
    )}, EventCategory.REPAY: {DEFAULT: EventCategoryDetails(
        label='repay',
        icon='lu-history',
    )}, EventCategory.DEPLOY: {DEFAULT: EventCategoryDetails(
        label='deploy',
        icon='lu-rocket',
    )}, EventCategory.DEPLOY_WITH_SPEND: {DEFAULT: EventCategoryDetails(
        label='deploy with spend',
        icon='lu-rocket',
    )}, EventCategory.BRIDGE_DEPOSIT: {DEFAULT: EventCategoryDetails(
        label='bridge',
        icon='lu-upload',
        color='error',
    )}, EventCategory.BRIDGE_WITHDRAWAL: {DEFAULT: EventCategoryDetails(
        label='bridge',
        icon='lu-download',
        color='success',
    )}, EventCategory.GOVERNANCE: {DEFAULT: EventCategoryDetails(
        label='governance',
        icon='lu-scale',
    )}, EventCategory.DONATE: {DEFAULT: EventCategoryDetails(
        label='donate',
        icon='lu-donate-fill',
    )}, EventCategory.RECEIVE_DONATION: {DEFAULT: EventCategoryDetails(
        label='receive donation',
        icon='lu-receive-donation-fill',
    )}, EventCategory.RENEW: {DEFAULT: EventCategoryDetails(
        label='renew',
        icon='lu-refresh-cw',
    )}, EventCategory.PLACE_ORDER: {DEFAULT: EventCategoryDetails(
        label='place order',
        icon='lu-briefcase',
    )}, EventCategory.TRANSFER: {DEFAULT: EventCategoryDetails(
        label='transfer',
        icon='lu-arrow-up-down',
    )}, EventCategory.STAKING_REWARD: {DEFAULT: EventCategoryDetails(
        label='staking reward',
        icon='lu-trophy',
    )}, EventCategory.CLAIM_REWARD: {DEFAULT: EventCategoryDetails(
        label='claim reward',
        icon='lu-gift',
    )}, EventCategory.LIQUIDATION_REWARD: {DEFAULT: EventCategoryDetails(
        label='liquidation reward',
        icon='lu-droplet-fill',
    )}, EventCategory.LIQUIDATION_LOSS: {DEFAULT: EventCategoryDetails(
        label='liquidation loss',
        icon='lu-droplet-half-fill',
    )}, EventCategory.INFORMATIONAL: {DEFAULT: EventCategoryDetails(
        label='informational',
        icon='lu-info',
    )}, EventCategory.CANCEL_ORDER: {DEFAULT: EventCategoryDetails(
        label='cancel order',
        icon='lu-file-x',
        color='error',
    )}, EventCategory.REFUND: {DEFAULT: EventCategoryDetails(
        label='refund',
        icon='lu-refund',
    )}, EventCategory.FEE: {
        DEFAULT: EventCategoryDetails(label='fee', icon='lu-banknote'),
        CPT_GAS: EventCategoryDetails(label='gas fee', icon='lu-flame'),
    }, EventCategory.FAIL: {DEFAULT: EventCategoryDetails(
        label='Failed',
        icon='lu-circle-x',
        color='error',
    )}, EventCategory.MEV_REWARD: {DEFAULT: EventCategoryDetails(
        label='mev',
        icon='lu-medal',
    )}, EventCategory.CREATE_BLOCK: {DEFAULT: EventCategoryDetails(
        label='new block',
        icon='lu-box',
    )}, EventCategory.CREATE_PROJECT: {DEFAULT: EventCategoryDetails(
        label='new project',
        icon='lu-file-plus',
    )}, EventCategory.UPDATE: {DEFAULT: EventCategoryDetails(
        label='update',
        icon='lu-square-pen',
    )}, EventCategory.APPLY: {DEFAULT: EventCategoryDetails(
        label='apply',
        icon='lu-circle-arrow-out-up-right',
    )}, EventCategory.STAKE_DEPOSIT: {DEFAULT: EventCategoryDetails(
        label='Stake',
        icon='lu-layers-in',
    )}, EventCategory.UNSTAKE: {DEFAULT: EventCategoryDetails(
        label='Unstake',
        icon='lu-layers-out',
    )}, EventCategory.STAKE_EXIT: {DEFAULT: EventCategoryDetails(
        label='exit',
        icon='lu-layers-out',
    )}, EventCategory.ATTEST: {DEFAULT: EventCategoryDetails(
        label='Attest',
        icon='lu-feather',
    )}, EventCategory.PAY: {DEFAULT: EventCategoryDetails(
        label='pay',
        icon='lu-upload',
    )}, EventCategory.RECEIVE_PAYMENT: {DEFAULT: EventCategoryDetails(
        label='receive payment',
        icon='lu-download',
    )}, EventCategory.RECEIVE_GRANT: {DEFAULT: EventCategoryDetails(
        label='receive grant',
        icon='lu-hand-coins',
    )}, EventCategory.INTEREST: {DEFAULT: EventCategoryDetails(
        label='receive interest',
        icon='lu-sprout',
    )}, EventCategory.CASHBACK: {DEFAULT: EventCategoryDetails(
        label='Cashback',
        icon='lu-badge-dollar-sign',
    )}, EventCategory.HACK_LOSS: {DEFAULT: EventCategoryDetails(
        label='Hack',
        icon='lu-skull',
    )}, EventCategory.CLAWBACK: {DEFAULT: EventCategoryDetails(
        label='Clawback',
        icon='lu-undo-2',
    )}, EventCategory.MINT_NFT: {DEFAULT: EventCategoryDetails(
        label='mint nft',
        icon='lu-file-image',
    )}, EventCategory.BURN: {DEFAULT: EventCategoryDetails(
        label='burn',
        icon='lu-flame-kindling',
    )}, EventCategory.COMBINE: {DEFAULT: EventCategoryDetails(
        label='Combine',
        icon='lu-combine',
    )}, EventCategory.DELEGATE: {DEFAULT: EventCategoryDetails(
        label='delegate',
        icon='lu-handshake',
    )}, EventCategory.LOSS: {DEFAULT: EventCategoryDetails(
        label='loss',
        icon='lu-trending-down',
    )}, EventCategory.LIQUIDITY_PROVISION_LOSS: {DEFAULT: EventCategoryDetails(
        label='liquidity provision loss',
        icon='lu-droplet-trending-down',
    )},
}

ACCOUNTING_EVENTS_ICONS = {
    AccountingEventType.TRADE: 'lu-send-to-back',
    AccountingEventType.FEE: 'lu-banknote',
    AccountingEventType.ASSET_MOVEMENT: 'lu-coins-exchange',
    AccountingEventType.MARGIN_POSITION: 'lu-percent',
    AccountingEventType.LOAN: 'lu-handshake',
    AccountingEventType.PREFORK_ACQUISITION: 'lu-git-branch',
    AccountingEventType.STAKING: 'lu-layers',
    AccountingEventType.HISTORY_EVENT: 'lu-history-events-fill',
    AccountingEventType.TRANSACTION_EVENT: 'lu-arrow-left-right',
}
