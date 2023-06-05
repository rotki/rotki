<script lang="ts" setup>
import { type Trade } from '@/types/history/trade';

const props = withDefaults(
  defineProps<{
    editableItem?: Trade | null;
    loading?: boolean;
  }>(),
  {
    editableItem: null,
    loading: false
  }
);

const { editableItem } = toRefs(props);

const { openDialog, submitting, closeDialog, trySubmit } = useTradesForm();

const { t } = useI18n();

const title: ComputedRef<string> = computed(() =>
  get(editableItem)
    ? t('closed_trades.dialog.edit.title')
    : t('closed_trades.dialog.add.title')
);

const subtitle: ComputedRef<string> = computed(() =>
  get(editableItem) ? t('closed_trades.dialog.edit.subtitle') : ''
);
</script>

<template>
  <big-dialog
    :display="openDialog"
    :title="title"
    :subtitle="subtitle"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading || submitting"
    :loading="loading || submitting"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <external-trade-form :editable-item="editableItem" />
  </big-dialog>
</template>
