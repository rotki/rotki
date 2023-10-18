import {
  type EditHistoryEventPayload,
  type NewHistoryEventPayload
} from '@/types/history/events';
import type HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';

export const useHistoryEventsForm = createSharedComposable(() => {
  const { setMessage } = useMessageStore();
  const { editHistoryEvent, addHistoryEvent } = useHistoryEvents();

  const saveHistoryEventHandler = async (
    payload: NewHistoryEventPayload | EditHistoryEventPayload,
    assetPriceForm: Ref<InstanceType<typeof HistoryEventAssetPriceForm> | null>,
    errorMessages: Ref<Record<string, string[]>>,
    reset: () => any
  ) => {
    const submitPriceResult = await get(assetPriceForm)!.submitPrice(payload);

    if (!submitPriceResult.success) {
      set(errorMessages, submitPriceResult.message);
      return false;
    }

    const edit = 'identifier' in payload;

    const result = !edit
      ? await addHistoryEvent(payload)
      : await editHistoryEvent(payload);

    if (result.success) {
      reset();
      return true;
    }

    if (result.message) {
      if (typeof result.message === 'string') {
        setMessage({
          description: result.message
        });
      } else {
        set(errorMessages, result.message);
      }
    }

    return false;
  };

  return {
    ...useForm<boolean>(),
    saveHistoryEventHandler
  };
});
