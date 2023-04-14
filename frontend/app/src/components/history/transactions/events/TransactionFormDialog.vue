<script lang="ts" setup>
import { type Ref } from 'vue';
import TransactionForm from '@/components/history/transactions/TransactionForm.vue';
import { type EvmChainAndTxHash } from '@/types/history/tx';

withDefaults(
  defineProps<{
    value: boolean;
    loading?: boolean;
  }>(),
  {
    loading: false
  }
);

const emit = defineEmits<{
  (e: 'input', open: boolean): void;
  (e: 'saved', data: EvmChainAndTxHash): void;
}>();

const valid: Ref<boolean> = ref(false);
const form = ref<InstanceType<typeof TransactionForm> | null>(null);

const clearDialog = () => {
  get(form)?.reset();
  emit('input', false);
};

const confirmSave = async () => {
  if (!isDefined(form)) {
    return;
  }
  const data = await get(form).save();
  if (data) {
    clearDialog();
    emit('saved', data);
  }
};

const { tc } = useI18n();
</script>

<template>
  <big-dialog
    :display="value"
    :title="tc('transactions.dialog.add_tx')"
    :primary-action="tc('common.actions.save')"
    :action-disabled="loading || form?.loading || !valid"
    :loading="loading || form?.loading"
    @confirm="confirmSave()"
    @cancel="clearDialog()"
  >
    <transaction-form ref="form" v-model="valid" />
  </big-dialog>
</template>
