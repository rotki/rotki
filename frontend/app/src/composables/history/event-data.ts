import { type ComputedRef } from 'vue';
import {
  HistoryEventSubType,
  HistoryEventType
} from '@rotki/common/lib/history/tx-events';
import { type ActionDataEntry } from '@/types/action';

export const useHistoryEventTypeData = createSharedComposable(() => {
  const { tc } = useI18n();
  const historyEventTypeData: ComputedRef<ActionDataEntry[]> = computed(() => [
    {
      identifier: HistoryEventType.TRADE,
      label: tc('transactions.events.history_event_type.trade')
    },
    {
      identifier: HistoryEventType.STAKING,
      label: tc('transactions.events.history_event_type.staking')
    },
    {
      identifier: HistoryEventType.DEPOSIT,
      label: tc('transactions.events.history_event_type.deposit')
    },
    {
      identifier: HistoryEventType.WITHDRAWAL,
      label: tc('transactions.events.history_event_type.withdrawal')
    },
    {
      identifier: HistoryEventType.TRANSFER,
      label: tc('transactions.events.history_event_type.transfer')
    },
    {
      identifier: HistoryEventType.SPEND,
      label: tc('transactions.events.history_event_type.spend')
    },
    {
      identifier: HistoryEventType.RECEIVE,
      label: tc('transactions.events.history_event_type.receive')
    },
    {
      identifier: HistoryEventType.ADJUSTMENT,
      label: tc('transactions.events.history_event_type.adjustment')
    },
    {
      identifier: HistoryEventType.UNKNOWN,
      label: tc('transactions.events.history_event_type.unknown')
    },
    {
      identifier: HistoryEventType.INFORMATIONAL,
      label: tc('transactions.events.history_event_type.informational')
    },
    {
      identifier: HistoryEventType.MIGRATE,
      label: tc('transactions.events.history_event_type.migrate')
    },
    {
      identifier: HistoryEventType.RENEW,
      label: tc('transactions.events.history_event_type.renew')
    }
  ]);

  const historyEventSubTypeData: ComputedRef<ActionDataEntry[]> = computed(
    () => [
      {
        identifier: HistoryEventSubType.NONE,
        label: tc('transactions.events.history_event_subtype.none')
      },
      {
        identifier: HistoryEventSubType.REWARD,
        label: tc('transactions.events.history_event_subtype.reward')
      },
      {
        identifier: HistoryEventSubType.DEPOSIT_ASSET,
        label: tc('transactions.events.history_event_subtype.deposit_asset')
      },
      {
        identifier: HistoryEventSubType.REMOVE_ASSET,
        label: tc('transactions.events.history_event_subtype.remove_asset')
      },
      {
        identifier: HistoryEventSubType.FEE,
        label: tc('transactions.events.history_event_subtype.fee')
      },
      {
        identifier: HistoryEventSubType.SPEND,
        label: tc('transactions.events.history_event_subtype.spend')
      },
      {
        identifier: HistoryEventSubType.RECEIVE,
        label: tc('transactions.events.history_event_subtype.receive')
      },
      {
        identifier: HistoryEventSubType.APPROVE,
        label: tc('transactions.events.history_event_subtype.approve')
      },
      {
        identifier: HistoryEventSubType.DEPLOY,
        label: tc('transactions.events.history_event_subtype.deploy')
      },
      {
        identifier: HistoryEventSubType.AIRDROP,
        label: tc('transactions.events.history_event_subtype.airdrop')
      },
      {
        identifier: HistoryEventSubType.BRIDGE,
        label: tc('transactions.events.history_event_subtype.bridge')
      },
      {
        identifier: HistoryEventSubType.GOVERNANCE,
        label: tc('transactions.events.history_event_subtype.governance')
      },
      {
        identifier: HistoryEventSubType.GENERATE_DEBT,
        label: tc('transactions.events.history_event_subtype.generate_debt')
      },
      {
        identifier: HistoryEventSubType.PAYBACK_DEBT,
        label: tc('transactions.events.history_event_subtype.payback_debt')
      },
      {
        identifier: HistoryEventSubType.RECEIVE_WRAPPED,
        label: tc('transactions.events.history_event_subtype.receive_wrapped')
      },
      {
        identifier: HistoryEventSubType.RETURN_WRAPPED,
        label: tc('transactions.events.history_event_subtype.return_wrapped')
      },
      {
        identifier: HistoryEventSubType.DONATE,
        label: tc('transactions.events.history_event_subtype.donate')
      },
      {
        identifier: HistoryEventSubType.NFT,
        label: tc('transactions.events.history_event_subtype.nft')
      },
      {
        identifier: HistoryEventSubType.PLACE_ORDER,
        label: tc('transactions.events.history_event_subtype.place_order')
      },
      {
        identifier: HistoryEventSubType.LIQUIDATE,
        label: tc('transactions.events.history_event_subtype.liquidate')
      }
    ]
  );

  return { historyEventTypeData, historyEventSubTypeData };
});
