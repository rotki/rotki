<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type LedgerActionEntry } from '@/types/history/ledger-action/ledger-actions';

const props = withDefaults(
  defineProps<{
    editableItem?: Partial<LedgerActionEntry> | null;
    loading?: boolean;
  }>(),
  {
    editableItem: null,
    loading: false
  }
);

const { editableItem } = toRefs(props);

const { valid, openDialog, submitting, closeDialog, trySubmit } =
  useLedgerActionsForm();

const { t } = useI18n();

const title: ComputedRef<string> = computed(() =>
  get(editableItem)
    ? t('ledger_actions.dialog.edit.title')
    : t('ledger_actions.dialog.add.title')
);

const subtitle: ComputedRef<string> = computed(() =>
  get(editableItem)
    ? t('ledger_actions.dialog.edit.subtitle')
    : t('ledger_actions.dialog.add.subtitle')
);
</script>

<template>
  <big-dialog
    :display="openDialog"
    :title="title"
    :subtitle="subtitle"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading || submitting || !valid"
    :loading="loading || submitting"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <ledger-action-form :editable-item="editableItem" />
  </big-dialog>
</template>
