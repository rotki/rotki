import type { Ref } from 'vue';
import type { DialogState } from './types';
import type { AddTransactionHashPayload } from '@/modules/history/events/event-payloads';
import type { AccountingRuleIdentifier } from '@/modules/settings/types/accounting';
import { set } from '@vueuse/core';
import { DIALOG_TYPES, type DialogShowOptions, type DialogType } from '@/modules/history/events/dialog-types';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

interface UseHistoryEventsDialogManager {
  show: (options: DialogShowOptions) => Promise<void>;
  currentDialog: Readonly<Ref<DialogState>>;
  closeDialog: () => void;
}

type OpenDialogState = Exclude<DialogState, { type: 'closed' }>;

type DatalessDialogType =
  | typeof DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES
  | typeof DIALOG_TYPES.INTERNAL_TX_CONFLICTS
  | typeof DIALOG_TYPES.MATCH_ASSET_MOVEMENTS
  | typeof DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS
  | typeof DIALOG_TYPES.PROTOCOL_CACHE
  | typeof DIALOG_TYPES.REPULLING_TRANSACTION;

const DATALESS_DIALOG_TYPES = new Set<DialogType>([
  DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES,
  DIALOG_TYPES.INTERNAL_TX_CONFLICTS,
  DIALOG_TYPES.MATCH_ASSET_MOVEMENTS,
  DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS,
  DIALOG_TYPES.PROTOCOL_CACHE,
  DIALOG_TYPES.REPULLING_TRANSACTION,
]);

function isDatalessDialogType(type: DialogType): type is DatalessDialogType {
  return DATALESS_DIALOG_TYPES.has(type);
}

function buildTransactionForm(data?: AddTransactionHashPayload): OpenDialogState {
  return {
    data: data ?? { associatedAddress: '', blockchain: '', txRef: '' },
    type: DIALOG_TYPES.TRANSACTION_FORM,
  };
}

/**
 * Maps show options to the dialog state to open, or `undefined` for options that
 * do not open a dialog directly (handled by the caller, e.g. add-missing-rule).
 */
function resolveDialogState(options: DialogShowOptions): OpenDialogState | undefined {
  if (isDatalessDialogType(options.type))
    return { data: undefined, type: options.type };

  switch (options.type) {
    case DIALOG_TYPES.EVENT_FORM:
      return { data: options.data, type: DIALOG_TYPES.EVENT_FORM };
    case DIALOG_TYPES.TRANSACTION_FORM:
      return buildTransactionForm(options.data);
    case DIALOG_TYPES.ADD_TRANSACTION:
      return buildTransactionForm();
    case DIALOG_TYPES.MISSING_RULES:
      return { data: options.data, type: DIALOG_TYPES.MISSING_RULES };
    case DIALOG_TYPES.DECODING_STATUS:
      return { data: { persistent: Boolean(options.persistent) }, type: DIALOG_TYPES.DECODING_STATUS };
    case DIALOG_TYPES.ADD_MISSING_RULE:
      return undefined;
  }
}

export function useHistoryEventsDialogManager(): UseHistoryEventsDialogManager {
  const router = useRouter();
  const internalTxConflicts = usePinnedPanel(PinnedNames.INTERNAL_TX_CONFLICTS);

  const currentDialog = ref<DialogState>({ type: 'closed' });

  function openDialog(state: OpenDialogState): void {
    set(currentDialog, state);
  }

  function closeDialog(): void {
    set(currentDialog, { type: 'closed' });
  }

  async function navigateToAddRule(data: AccountingRuleIdentifier): Promise<void> {
    const { eventIds, ...restData } = data;
    await router.push({
      path: '/settings/accounting',
      query: { 'add-rule': 'true', 'eventId': eventIds ? eventIds[0].toString() : undefined, ...restData },
    });
  }

  async function show(options: DialogShowOptions): Promise<void> {
    if (options.type === DIALOG_TYPES.ADD_MISSING_RULE) {
      await navigateToAddRule(options.data);
      return;
    }

    // Already pinned: bring its tab to the front instead of reopening the dialog.
    if (options.type === DIALOG_TYPES.INTERNAL_TX_CONFLICTS && get(internalTxConflicts.isPinned)) {
      internalTxConflicts.focus();
      return;
    }

    const state = resolveDialogState(options);
    if (state)
      openDialog(state);
  }

  return {
    closeDialog,
    currentDialog: shallowReadonly(currentDialog),
    show,
  };
}
