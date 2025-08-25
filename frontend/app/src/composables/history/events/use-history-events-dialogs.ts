import type { Ref } from 'vue';
import type {
  GroupEventData,
  HistoryEventEditData,
  ShowEventHistoryForm,
  ShowFormData,
  StandaloneEventData,
} from '@/modules/history/management/forms/form-types';
import type {
  AddTransactionHashPayload,
} from '@/types/history/events';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import { startPromise } from '@shared/utils';

interface UseHistoryEventsDialogs {
  addTransactionModelValue: Ref<AddTransactionHashPayload | undefined>;
  addTxHash: () => void;
  decodingStatusDialogOpen: Ref<boolean>;
  decodingStatusDialogPersistent: Ref<boolean>;
  editMissingRulesEntry: (data: ShowFormData) => void;
  formData: Ref<GroupEventData | StandaloneEventData | undefined>;
  missingRuleData: Ref<HistoryEventEditData | undefined>;
  onAddMissingRule: (data: Pick<AccountingRuleEntry, 'eventType' | 'eventSubtype' | 'counterparty'>) => void;
  onShowDialog: (type: 'decode' | 'protocol-refresh') => void;
  protocolCacheStatusDialogOpen: Ref<boolean>;
  showForm: (payload: ShowEventHistoryForm) => void;
  showRePullTransactionsDialog: Ref<boolean>;
}

export function useHistoryEventsDialogs(): UseHistoryEventsDialogs {
  const router = useRouter();

  // Dialog state
  const formData = ref<GroupEventData | StandaloneEventData>();
  const missingRuleData = ref<HistoryEventEditData>();
  const decodingStatusDialogPersistent = ref<boolean>(false);
  const decodingStatusDialogOpen = ref<boolean>(false);
  const protocolCacheStatusDialogOpen = ref<boolean>(false);
  const addTransactionModelValue = ref<AddTransactionHashPayload>();
  const showRePullTransactionsDialog = ref<boolean>(false);

  // Methods
  function showForm(payload: ShowEventHistoryForm): void {
    if (payload.type === 'event') {
      set(formData, payload.data);
    }
    else {
      set(missingRuleData, payload.data);
    }
  }

  async function onAddMissingRule(data: Pick<AccountingRuleEntry, 'eventType' | 'eventSubtype' | 'counterparty'>): Promise<void> {
    await router.push({
      path: '/settings/accounting',
      query: { 'add-rule': 'true', ...data },
    });
  }

  function editMissingRulesEntry(data: ShowFormData): void {
    startPromise(nextTick(() => {
      showForm({ data, type: 'event' });
    }));
  }

  function onShowDialog(type: 'decode' | 'protocol-refresh'): void {
    if (type === 'decode')
      set(decodingStatusDialogOpen, true);
    else
      set(protocolCacheStatusDialogOpen, true);
  }

  function addTxHash(): void {
    set(addTransactionModelValue, {
      associatedAddress: '',
      evmChain: '',
      txHash: '',
    });
  }

  return {
    addTransactionModelValue,
    addTxHash,
    decodingStatusDialogOpen,
    decodingStatusDialogPersistent,
    editMissingRulesEntry,
    formData,
    missingRuleData,
    onAddMissingRule,
    onShowDialog,
    protocolCacheStatusDialogOpen,
    showForm,
    showRePullTransactionsDialog,
  };
}
