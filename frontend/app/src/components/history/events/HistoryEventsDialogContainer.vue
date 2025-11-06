<script setup lang="ts">
import type { HistoryEventAction } from '@/composables/history/events/types';
import type { AddTransactionHashPayload } from '@/types/history/events';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import { get } from '@vueuse/core';
import { useHistoryEventsDialogManager } from '@/composables/history/events/dialog-manager/use-history-events-dialog-manager';
import { DIALOG_TYPES, type DialogEventHandlers } from './dialog-types';

const accountingRuleToEdit = defineModel<AccountingRuleEntry | undefined>('accountingRuleToEdit', { required: true });
const currentAction = defineModel<HistoryEventAction>('currentAction', { required: true });

withDefaults(defineProps<{
  eventHandlers?: DialogEventHandlers;
  loading?: boolean;
  refreshing?: boolean;
  sectionLoading?: boolean;
  selectedEventIds?: number[];
}>(), {
  eventHandlers: () => ({}),
  loading: false,
  refreshing: false,
  sectionLoading: false,
  selectedEventIds: () => [],
});

const emit = defineEmits<{
  'accounting-rule-refresh': [];
}>();

// Shared loading component for lazy-loaded dialogs
function DialogLoadingComponent() {
  return h('div', { class: 'flex items-center justify-center p-4' }, h('RuiProgress', { circular: true, size: 40, variant: 'indeterminate' }));
}

// Lazy load heavy dialog components
const MissingRulesDialog = defineAsyncComponent({
  delay: 200,
  loader: () => import('@/components/dialogs/MissingRulesDialog.vue'),
  loadingComponent: DialogLoadingComponent,
});

const HistoryEventFormDialog = defineAsyncComponent({
  delay: 200,
  loader: () => import('@/components/history/events/HistoryEventFormDialog.vue'),
  loadingComponent: DialogLoadingComponent,
});

const HistoryEventsDecodingStatusDialog = defineAsyncComponent(() => import('@/components/history/events/HistoryEventsDecodingStatusDialog.vue'));

const HistoryEventsProtocolCacheStatusDialog = defineAsyncComponent(
  () => import('@/components/history/events/HistoryEventsProtocolCacheStatusDialog.vue'),
);

const RepullingTransactionFormDialog = defineAsyncComponent({
  delay: 200,
  loader: () => import('@/components/history/events/tx/RepullingTransactionFormDialog.vue'),
  loadingComponent: DialogLoadingComponent,
});

const TransactionFormDialog = defineAsyncComponent({
  delay: 200,
  loader: () => import('@/components/history/events/tx/TransactionFormDialog.vue'),
  loadingComponent: DialogLoadingComponent,
});

const AccountingRuleFormDialog = defineAsyncComponent({
  delay: 200,
  loader: () => import('@/components/settings/accounting/rule/AccountingRuleFormDialog.vue'),
  loadingComponent: DialogLoadingComponent,
});

const {
  closeDialog,
  currentDialog,
  show: managerShow,
} = useHistoryEventsDialogManager();

// Type-specific computed properties for each dialog
// Since dialogs only render when they match the type (v-if), we can safely use type assertions
const formData = computed({
  get: () => {
    const dialog = get(currentDialog);
    return dialog.type === DIALOG_TYPES.EVENT_FORM ? dialog.data : undefined;
  },
  set: () => closeDialog(), // Dialog components handle their own closing
});

const missingRuleData = computed({
  get: () => {
    const dialog = get(currentDialog);
    return dialog.type === DIALOG_TYPES.MISSING_RULES ? dialog.data : undefined;
  },
  set: () => closeDialog(),
});

// Unified computed for dialogs that are always "open" when rendered
const dialogIsOpen = computed({
  get: () => true, // Always true when dialog is rendered (due to v-if)
  set: () => closeDialog(),
});

const decodingStatusDialogPersistent = computed(() => {
  const dialog = get(currentDialog);
  return dialog.type === DIALOG_TYPES.DECODING_STATUS ? (dialog.data?.persistent || false) : false;
});

const addTransactionModelValue = computed({
  get: () => {
    const dialog = get(currentDialog);
    return dialog.type === DIALOG_TYPES.TRANSACTION_FORM ? dialog.data : undefined;
  },
  set: (value: AddTransactionHashPayload | undefined) => {
    if (value) {
      managerShow({ data: value, type: DIALOG_TYPES.TRANSACTION_FORM });
    }
    else {
      closeDialog();
    }
  },
});

defineExpose({
  show: managerShow,
});
</script>

<template>
  <div class="history-events-dialog-container">
    <HistoryEventFormDialog
      v-if="currentDialog.type === DIALOG_TYPES.EVENT_FORM"
      v-model="formData"
      :loading="loading"
      @refresh="eventHandlers.onHistoryEventSaved?.()"
    />

    <TransactionFormDialog
      v-if="currentDialog.type === DIALOG_TYPES.TRANSACTION_FORM"
      v-model="addTransactionModelValue"
      :loading="sectionLoading"
      @reload="eventHandlers.onTransactionAdded?.($event)"
    />

    <RepullingTransactionFormDialog
      v-if="currentDialog.type === DIALOG_TYPES.REPULLING_TRANSACTION"
      v-model="dialogIsOpen"
      v-model:current-action="currentAction"
      :loading="sectionLoading"
      :event-handlers="eventHandlers"
    />

    <MissingRulesDialog
      v-if="currentDialog.type === DIALOG_TYPES.MISSING_RULES"
      v-model="missingRuleData"
      @edit-event="managerShow({ data: $event, type: DIALOG_TYPES.EVENT_FORM })"
      @redecode="eventHandlers.onRedecodeTransaction?.($event)"
      @add="managerShow({ data: $event, type: DIALOG_TYPES.ADD_MISSING_RULE })"
      @dismiss="closeDialog()"
    />

    <HistoryEventsDecodingStatusDialog
      v-if="currentDialog.type === DIALOG_TYPES.DECODING_STATUS"
      v-model="dialogIsOpen"
      :refreshing="refreshing"
      :persistent="decodingStatusDialogPersistent"
      @redecode-all-events="eventHandlers.onRedecodeAllEvents?.()"
      @reset-undecoded-transactions="eventHandlers.onResetUndecodedTransactions?.()"
    />

    <HistoryEventsProtocolCacheStatusDialog
      v-if="currentDialog.type === DIALOG_TYPES.PROTOCOL_CACHE"
      v-model="dialogIsOpen"
      :refreshing="refreshing"
    />

    <AccountingRuleFormDialog
      v-model="accountingRuleToEdit"
      :event-ids="selectedEventIds"
      @refresh="emit('accounting-rule-refresh')"
    />
  </div>
</template>
