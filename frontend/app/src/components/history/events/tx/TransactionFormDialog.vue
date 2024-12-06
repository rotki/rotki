<script lang="ts" setup>
import { useHistoryTransactionsForm } from '@/composables/history/events/tx/form';
import TransactionForm from '@/components/history/events/tx/TransactionForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';

withDefaults(
  defineProps<{
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const { closeDialog, openDialog, stateUpdated, submitting, trySubmit } = useHistoryTransactionsForm();

const { t } = useI18n();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="t('transactions.dialog.add_tx')"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <TransactionForm />
  </BigDialog>
</template>
