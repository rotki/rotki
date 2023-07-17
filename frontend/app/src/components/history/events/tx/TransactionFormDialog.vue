<script lang="ts" setup>
withDefaults(
  defineProps<{
    loading?: boolean;
  }>(),
  {
    loading: false
  }
);

const { openDialog, submitting, closeDialog, trySubmit } =
  useHistoryTransactionsForm();

const { t } = useI18n();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="t('transactions.dialog.add_tx')"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <TransactionForm />
  </BigDialog>
</template>
