import type { ShallowRef } from 'vue';
import type SwapSubEventList from '@/modules/history/management/forms/swap/SwapSubEventList.vue';
import type { ValidationErrors } from '@/types/api/errors';
import type { SwapSubEventModel } from '@/types/history/events/schemas';
import { useHistoryEvents } from '@/composables/history/events';
import { useMessageStore } from '@/store/message';

export interface SwapEventFormListRefs {
  spendListRef: Readonly<ShallowRef<InstanceType<typeof SwapSubEventList> | null>>;
  receiveListRef: Readonly<ShallowRef<InstanceType<typeof SwapSubEventList> | null>>;
  feeListRef: Readonly<ShallowRef<InstanceType<typeof SwapSubEventList> | null>>;
}

interface UseSwapEventFormReturn {
  emptySubEvent: () => SwapSubEventModel;
  handleValidationErrors: (message: ValidationErrors | string) => void;
  submitAllPrices: (listRefs: SwapEventFormListRefs) => Promise<boolean>;
  addHistoryEvent: ReturnType<typeof useHistoryEvents>['addHistoryEvent'];
  editHistoryEvent: ReturnType<typeof useHistoryEvents>['editHistoryEvent'];
}

/**
 * Composable for swap event forms (EVM and Solana) that provides:
 * - Empty sub-event factory
 * - Validation error handling
 * - Price submission for all sub-events
 * - History event add/edit functions
 */
export function useSwapEventForm(): UseSwapEventFormReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { setMessage } = useMessageStore();
  const { addHistoryEvent, editHistoryEvent } = useHistoryEvents();

  function emptySubEvent(): SwapSubEventModel {
    return {
      amount: '',
      asset: '',
    };
  }

  function handleValidationErrors(message: ValidationErrors | string): void {
    if (typeof message === 'string') {
      setMessage({
        description: message,
      });
    }
  }

  async function submitAllPrices(listRefs: SwapEventFormListRefs): Promise<boolean> {
    const lists = [
      get(listRefs.spendListRef),
      get(listRefs.receiveListRef),
      get(listRefs.feeListRef),
    ].filter(Boolean);

    for (const list of lists) {
      if (!list)
        continue;
      const subEvents = list.getSubEventRefs();
      for (const subEvent of subEvents) {
        const result = await subEvent.submitPrice();
        if (result && !result.success) {
          handleValidationErrors(result.message || t('transactions.events.form.asset_price.failed'));
          return false;
        }
      }
    }

    return true;
  }

  return {
    emptySubEvent,
    handleValidationErrors,
    submitAllPrices,
    addHistoryEvent,
    editHistoryEvent,
  };
}
