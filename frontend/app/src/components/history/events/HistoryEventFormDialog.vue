<script lang="ts" setup>
import { type HistoryEvent } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    editableItem?: HistoryEvent;
    nextSequence?: string;
    loading?: boolean;
    groupHeader?: HistoryEvent;
  }>(),
  {
    editableItem: undefined,
    nextSequence: undefined,
    loading: false,
    groupHeader: undefined
  }
);

const { editableItem, groupHeader } = toRefs(props);

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
    :action-disabled="loading"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <HistoryEventForm
      :group-header="groupHeader"
      :editable-item="editableItem"
      :next-sequence="nextSequence"
    />
  </BigDialog>
</template>
