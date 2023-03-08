import {
  HistoryEventSubType,
  HistoryEventType,
  TransactionEventType
} from '@rotki/common/lib/history/tx-events';

export const transactionEventTypeMapping: Record<
  string,
  Record<string, TransactionEventType>
> = {
  [HistoryEventType.SPEND]: {
    [HistoryEventSubType.FEE]: TransactionEventType.GAS,
    [HistoryEventSubType.PAYBACK_DEBT]: TransactionEventType.REPAY,
    [HistoryEventSubType.RETURN_WRAPPED]: TransactionEventType.SEND,
    [HistoryEventSubType.DONATE]: TransactionEventType.DONATE,
    [HistoryEventSubType.LIQUIDATE]: TransactionEventType.LIQUIDATE,
    [HistoryEventSubType.NONE]: TransactionEventType.SEND
  },
  [HistoryEventType.RECEIVE]: {
    [HistoryEventSubType.GENERATE_DEBT]: TransactionEventType.BORROW,
    [HistoryEventSubType.RECEIVE_WRAPPED]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.RETURN_WRAPPED]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.AIRDROP]: TransactionEventType.AIRDROP,
    [HistoryEventSubType.REWARD]: TransactionEventType.CLAIM_REWARD,
    [HistoryEventSubType.NONE]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.DONATE]: TransactionEventType.RECEIVE_DONATION,
    [HistoryEventSubType.NFT]: TransactionEventType.RECEIVE
  },
  [HistoryEventType.INFORMATIONAL]: {
    [HistoryEventSubType.APPROVE]: TransactionEventType.APPROVAL,
    [HistoryEventSubType.GOVERNANCE]: TransactionEventType.GOVERNANCE,
    [HistoryEventSubType.DEPLOY]: TransactionEventType.DEPLOY,
    [HistoryEventSubType.REMOVE_ASSET]: TransactionEventType.WITHDRAW,
    [HistoryEventSubType.PLACE_ORDER]: TransactionEventType.PLACE_ORDER,
    [HistoryEventSubType.NONE]: TransactionEventType.INFORMATIONAL
  },
  [HistoryEventType.TRANSFER]: {
    [HistoryEventSubType.NONE]: TransactionEventType.TRANSFER,
    [HistoryEventSubType.BRIDGE]: TransactionEventType.BRIDGE
  },
  [HistoryEventType.TRADE]: {
    [HistoryEventSubType.SPEND]: TransactionEventType.SWAP_OUT,
    [HistoryEventSubType.RECEIVE]: TransactionEventType.SWAP_IN
  },
  [HistoryEventType.WITHDRAWAL]: {
    [HistoryEventSubType.NONE]: TransactionEventType.WITHDRAW,
    [HistoryEventSubType.REMOVE_ASSET]: TransactionEventType.WITHDRAW,
    [HistoryEventSubType.GENERATE_DEBT]: TransactionEventType.BORROW,
    [HistoryEventSubType.BRIDGE]: TransactionEventType.BRIDGE,
    [HistoryEventSubType.CANCEL_ORDER]: TransactionEventType.CANCEL_ORDER,
    [HistoryEventSubType.REFUND]: TransactionEventType.REFUND
  },
  [HistoryEventType.DEPOSIT]: {
    [HistoryEventSubType.NONE]: TransactionEventType.DEPOSIT,
    [HistoryEventSubType.DEPOSIT_ASSET]: TransactionEventType.DEPOSIT,
    [HistoryEventSubType.BRIDGE]: TransactionEventType.BRIDGE,
    [HistoryEventSubType.PLACE_ORDER]: TransactionEventType.PLACE_ORDER
  },
  [HistoryEventType.MIGRATE]: {
    [HistoryEventSubType.SPEND]: TransactionEventType.SEND,
    [HistoryEventSubType.RECEIVE]: TransactionEventType.RECEIVE
  },
  [HistoryEventType.RENEW]: {
    [HistoryEventSubType.NFT]: TransactionEventType.RENEW
  },
  [HistoryEventType.STAKING]: {
    [HistoryEventSubType.DEPOSIT_ASSET]: TransactionEventType.DEPOSIT,
    [HistoryEventSubType.REWARD]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.RECEIVE_WRAPPED]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.REMOVE_ASSET]: TransactionEventType.WITHDRAW,
    [HistoryEventSubType.RETURN_WRAPPED]: TransactionEventType.SEND
  }
};
