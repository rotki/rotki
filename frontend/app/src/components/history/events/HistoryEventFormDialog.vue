<script lang="ts" setup>
import { type EvmHistoryEvent } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    editableItem?: EvmHistoryEvent | null;
    nextSequence?: string | null;
    loading?: boolean;
    transaction: EvmHistoryEvent;
  }>(),
  {
    editableItem: null,
    nextSequence: null,
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
  <BigDialog
    :display="openDialog"
    :title="title"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading && !editableItem"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <HistoryEventForm
      :transaction="transaction"
      :editable-item="editableItem"
      :next-sequence="nextSequence"
    />
  </BigDialog>
</template>
