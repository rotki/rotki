<script lang="ts" setup>
import type { HistoryEvent, HistoryEventEntry } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    editableItem?: HistoryEventEntry;
    nextSequence?: string;
    loading?: boolean;
    groupHeader?: HistoryEvent;
  }>(),
  {
    editableItem: undefined,
    nextSequence: undefined,
    loading: false,
    groupHeader: undefined,
  },
);

const { editableItem, groupHeader } = toRefs(props);

const { openDialog, submitting, closeDialog, trySubmit, defaultNotes } = useHistoryEventsForm();

const { t } = useI18n();

const title = computed<string>(() =>
  get(editableItem) ? t('transactions.events.dialog.edit.title') : t('transactions.events.dialog.add.title'),
);

watchImmediate(editableItem, (editable) => {
  set(defaultNotes, editable?.defaultNotes);
});
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
      :default-notes="defaultNotes"
    />
  </BigDialog>
</template>
