<script lang="ts" setup>
import {
  type EvmChainAndTxHash,
  type HistoryEvent,
  type HistoryEventEntry
} from '@/types/history/events';
import type TransactionEventForm from '@/components/history/events/HistoryEventForm.vue';

const props = withDefaults(
  defineProps<{
    value: boolean;
    editableItem?: HistoryEvent | null;
    loading?: boolean;
    transaction: HistoryEventEntry;
  }>(),
  {
    editableItem: null,
    loading: false
  }
);

const { editableItem, transaction } = toRefs(props);

const emit = defineEmits<{
  (e: 'input', open: boolean): void;
  (e: 'reset-edit'): void;
  (e: 'saved', item: EvmChainAndTxHash): void;
}>();

const valid: Ref<boolean> = ref(false);
const form = ref<InstanceType<typeof TransactionEventForm> | null>(null);

const clearDialog = () => {
  get(form)?.reset();
  emit('input', false);
  emit('reset-edit');
};

const confirmSave = async () => {
  if (!isDefined(form)) {
    return;
  }
  const success = await get(form)?.save();
  if (success) {
    const tx = get(transaction);
    clearDialog();
    emit('saved', toEvmChainAndTxHash(tx));
  }
};

const { tc } = useI18n();

const title: ComputedRef<string> = computed(() =>
  get(editableItem)
    ? tc('transactions.events.dialog.edit.title')
    : tc('transactions.events.dialog.add.title')
);
</script>

<template>
  <big-dialog
    :display="value"
    :title="title"
    :primary-action="tc('common.actions.save')"
    :action-disabled="loading || !valid"
    :loading="loading"
    @confirm="confirmSave()"
    @cancel="clearDialog()"
  >
    <history-event-form
      ref="form"
      v-model="valid"
      :transaction="transaction"
      :edit="editableItem"
    />
  </big-dialog>
</template>
