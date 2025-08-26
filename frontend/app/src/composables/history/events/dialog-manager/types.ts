import type { DIALOG_TYPES } from '@/components/history/events/dialog-types';
import type {
  GroupEventData,
  HistoryEventEditData,
  StandaloneEventData,
} from '@/modules/history/management/forms/form-types';
import type { AddTransactionHashPayload } from '@/types/history/events';

export type DialogState =
  | { type: typeof DIALOG_TYPES.EVENT_FORM; data: GroupEventData | StandaloneEventData }
  | { type: typeof DIALOG_TYPES.TRANSACTION_FORM; data: AddTransactionHashPayload }
  | { type: typeof DIALOG_TYPES.REPULLING_TRANSACTION; data: undefined }
  | { type: typeof DIALOG_TYPES.MISSING_RULES; data: HistoryEventEditData }
  | { type: typeof DIALOG_TYPES.DECODING_STATUS; data: { persistent: boolean } }
  | { type: typeof DIALOG_TYPES.PROTOCOL_CACHE; data: undefined }
  | { type: 'closed' };
