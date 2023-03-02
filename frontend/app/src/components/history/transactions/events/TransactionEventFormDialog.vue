<script lang="ts" setup>
import { type ComputedRef, type Ref } from 'vue';
import {
  type EthTransactionEntry,
  type EthTransactionEvent
} from '@/types/history/tx';
import TransactionEventForm from '@/components/history/transactions/events/TransactionEventForm.vue';

const props = withDefaults(
  defineProps<{
    value: boolean;
    editableItem?: EthTransactionEvent | null;
    loading?: boolean;
    transaction?: EthTransactionEntry | null;
  }>(),
  {
    editableItem: null,
    loading: false,
    transaction: null
  }
);

const { editableItem } = toRefs(props);

const emit = defineEmits<{
  (e: 'input', open: boolean): void;
  (e: 'reset-edit'): void;
  (e: 'saved'): void;
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
    clearDialog();
    emit('saved');
  }
};

const { tc } = useI18n();

const title: ComputedRef<string> = computed(() => {
  return get(editableItem)
    ? tc('transactions.events.dialog.edit.title')
    : tc('transactions.events.dialog.add.title');
});
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
    <transaction-event-form
      ref="form"
      v-model="valid"
      :transaction="transaction"
      :edit="editableItem"
    />
  </big-dialog>
</template>
