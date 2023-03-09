import { type ComputedRef } from 'vue';
import { TransactionEventType } from '@rotki/common/lib/history/tx-events';
import { type ActionDataEntry } from '@/types/action';

export const useTransactionEventTypeData = createSharedComposable(() => {
  const { tc } = useI18n();
  const transactionEventTypeData: ComputedRef<ActionDataEntry[]> = computed(
    () => [
      {
        identifier: TransactionEventType.GAS,
        label: tc('transactions.events.type.gas_fee'),
        icon: 'mdi-fire'
      },
      {
        identifier: TransactionEventType.SEND,
        label: tc('transactions.events.type.send'),
        icon: 'mdi-arrow-up'
      },
      {
        identifier: TransactionEventType.RECEIVE,
        label: tc('transactions.events.type.receive'),
        icon: 'mdi-arrow-down',
        color: 'green'
      },
      {
        identifier: TransactionEventType.SWAP_OUT,
        label: tc('transactions.events.type.swap_out'),
        icon: 'mdi-arrow-u-right-bottom'
      },
      {
        identifier: TransactionEventType.SWAP_IN,
        label: tc('transactions.events.type.swap_in'),
        icon: 'mdi-arrow-u-left-top',
        color: 'green'
      },
      {
        identifier: TransactionEventType.APPROVAL,
        label: tc('transactions.events.type.approval'),
        icon: 'mdi-lock-open-outline'
      },
      {
        identifier: TransactionEventType.DEPOSIT,
        label: tc('transactions.events.type.deposit'),
        icon: 'mdi-arrow-expand-up',
        color: 'green'
      },
      {
        identifier: TransactionEventType.WITHDRAW,
        label: tc('transactions.events.type.withdraw'),
        icon: 'mdi-arrow-expand-down'
      },
      {
        identifier: TransactionEventType.AIRDROP,
        label: tc('transactions.events.type.airdrop'),
        icon: 'mdi-airballoon-outline'
      },
      {
        identifier: TransactionEventType.BORROW,
        label: tc('transactions.events.type.borrow'),
        icon: 'mdi-hand-coin-outline'
      },
      {
        identifier: TransactionEventType.REPAY,
        label: tc('transactions.events.type.repay'),
        icon: 'mdi-history'
      },
      {
        identifier: TransactionEventType.DEPLOY,
        label: tc('transactions.events.type.deploy'),
        icon: 'mdi-swap-horizontal'
      },
      {
        identifier: TransactionEventType.BRIDGE,
        label: tc('transactions.events.type.bridge'),
        icon: 'mdi-bridge'
      },
      {
        identifier: TransactionEventType.GOVERNANCE,
        label: tc('transactions.events.type.governance'),
        icon: 'mdi-bank'
      },
      {
        identifier: TransactionEventType.DONATE,
        label: tc('transactions.events.type.donate'),
        icon: 'mdi-hand-heart-outline'
      },
      {
        identifier: TransactionEventType.RECEIVE_DONATION,
        label: tc('transactions.events.type.receive_donation'),
        icon: 'mdi-hand-heart-outline'
      },
      {
        identifier: TransactionEventType.RENEW,
        label: tc('transactions.events.type.renew'),
        icon: 'mdi-calendar-refresh'
      },
      {
        identifier: TransactionEventType.PLACE_ORDER,
        label: tc('transactions.events.type.place_order'),
        icon: 'mdi-briefcase-arrow-up-down'
      },
      {
        identifier: TransactionEventType.TRANSFER,
        label: tc('transactions.events.type.transfer'),
        icon: 'mdi-swap-horizontal'
      },
      {
        identifier: TransactionEventType.CLAIM_REWARD,
        label: tc('transactions.events.type.claim_reward'),
        icon: 'mdi-gift'
      },
      {
        identifier: TransactionEventType.LIQUIDATE,
        label: tc('transactions.events.type.liquidate'),
        icon: 'mdi-water'
      },
      {
        identifier: TransactionEventType.INFORMATIONAL,
        label: tc('transactions.events.type.informational'),
        icon: 'mdi-information-outline'
      },
      {
        identifier: TransactionEventType.CANCEL_ORDER,
        label: tc('transactions.events.type.cancel_order'),
        icon: 'mdi-close-circle-multiple-outline',
        color: 'red'
      },
      {
        identifier: TransactionEventType.REFUND,
        label: tc('transactions.events.type.refund'),
        icon: 'mdi-cash-refund'
      }
    ]
  );

  return {
    transactionEventTypeData
  };
});
