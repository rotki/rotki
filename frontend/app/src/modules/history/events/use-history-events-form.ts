import type { ShallowRef } from 'vue';
import type { EditHistoryEventPayload, NewHistoryEventPayload } from '@/modules/history/events/schemas';
import type HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';

export const useHistoryEventsForm = createSharedComposable(() => {
  const { showErrorMessage } = useNotifications();
  const { addHistoryEvent, editHistoryEvent } = useHistoryEvents();

  const saveHistoryEventHandler = async (
    payload: NewHistoryEventPayload | EditHistoryEventPayload,
    assetPriceForm: Readonly<ShallowRef<InstanceType<typeof HistoryEventAssetPriceForm> | null>>,
    errorMessages: Ref<Record<string, string[]>>,
    reset: () => any,
    shouldSkipEdit: boolean,
  ): Promise<boolean> => {
    const submitPriceResult = await get(assetPriceForm)!.submitPrice(payload);

    if (!submitPriceResult.success) {
      set(errorMessages, submitPriceResult.message);
      return false;
    }

    const edit = 'identifier' in payload;

    if (edit && shouldSkipEdit) {
      reset();
      return true;
    }

    const result = !edit ? await addHistoryEvent(payload) : await editHistoryEvent(payload);

    if (result.success) {
      reset();
      return true;
    }

    if (result.message) {
      if (typeof result.message === 'string') {
        showErrorMessage(result.message);
      }
      else {
        set(errorMessages, result.message);
      }
    }

    return false;
  };

  return {
    saveHistoryEventHandler,
  };
});
