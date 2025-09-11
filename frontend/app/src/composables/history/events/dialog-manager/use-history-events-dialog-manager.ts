import type { Ref } from 'vue';
import type { DialogState } from './types';
import { set } from '@vueuse/core';
import { DIALOG_TYPES, type DialogShowOptions } from '@/components/history/events/dialog-types';

interface UseHistoryEventsDialogManager {
  show: (options: DialogShowOptions) => Promise<void>;
  currentDialog: Ref<DialogState>;
  closeDialog: () => void;
}

export function useHistoryEventsDialogManager(): UseHistoryEventsDialogManager {
  const router = useRouter();

  const currentDialog = ref<DialogState>({ type: 'closed' });

  function openDialog(state: Exclude<DialogState, { type: 'closed' }>): void {
    set(currentDialog, state);
  }

  function closeDialog(): void {
    set(currentDialog, { type: 'closed' });
  }

  async function show(options: DialogShowOptions): Promise<void> {
    switch (options.type) {
      case DIALOG_TYPES.EVENT_FORM:
        openDialog({ data: options.data, type: DIALOG_TYPES.EVENT_FORM });
        break;
      case DIALOG_TYPES.TRANSACTION_FORM:
        openDialog({
          data: options.data || {
            associatedAddress: '',
            blockchain: '',
            txRef: '',
          },
          type: DIALOG_TYPES.TRANSACTION_FORM,
        });
        break;
      case DIALOG_TYPES.REPULLING_TRANSACTION:
        openDialog({ data: undefined, type: DIALOG_TYPES.REPULLING_TRANSACTION });
        break;
      case DIALOG_TYPES.MISSING_RULES:
        openDialog({ data: options.data, type: DIALOG_TYPES.MISSING_RULES });
        break;
      case DIALOG_TYPES.DECODING_STATUS:
        openDialog({ data: { persistent: options.persistent || false }, type: DIALOG_TYPES.DECODING_STATUS });
        break;
      case DIALOG_TYPES.PROTOCOL_CACHE:
        openDialog({ data: undefined, type: DIALOG_TYPES.PROTOCOL_CACHE });
        break;
      case DIALOG_TYPES.ADD_TRANSACTION:
        openDialog({
          data: {
            associatedAddress: '',
            blockchain: '',
            txRef: '',
          },
          type: DIALOG_TYPES.TRANSACTION_FORM,
        });
        break;
      case DIALOG_TYPES.ADD_MISSING_RULE: {
        const { identifier, ...restData } = options.data;
        await router.push({
          path: '/settings/accounting',
          query: { 'add-rule': 'true', 'eventId': identifier.toString(), ...restData },
        });
        break;
      }
      default:
        break;
    }
  }

  return {
    closeDialog,
    currentDialog,
    show,
  };
}
