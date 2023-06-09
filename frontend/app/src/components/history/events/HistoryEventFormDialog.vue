<script lang="ts" setup>
import { type EvmHistoryEvent } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    editableItem?: EvmHistoryEvent | null;
    loading?: boolean;
    transaction: EvmHistoryEvent;
  }>(),
  {
    editableItem: null,
    loading: false
  }
);

const { editableItem, transaction } = toRefs(props);

const { openDialog, submitting, closeDialog, trySubmit } =
  useHistoryEventsForm();

const { t } = useI18n();

const title: ComputedRef<string> = computed(() =>
  get(editableItem)
    ? t('transactions.events.dialog.edit.title')
    : t('transactions.events.dialog.add.title')
);
</script>

<template>
  <big-dialog
    :display="openDialog"
    :title="title"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <history-event-form
      :transaction="transaction"
      :editable-item="editableItem"
    />
  </big-dialog>
</template>
