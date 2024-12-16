<script lang="ts" setup>
import { useHistoryEventsForm } from '@/composables/history/events/form';
import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import type { HistoryEvent, HistoryEventEntry } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    editableItem?: HistoryEventEntry;
    nextSequence?: string;
    loading?: boolean;
    groupHeader?: HistoryEvent;
    groupEvents?: HistoryEvent[];
  }>(),
  {
    editableItem: undefined,
    groupEvents: undefined,
    groupHeader: undefined,
    loading: false,
    nextSequence: undefined,
  },
);

const { editableItem, groupHeader } = toRefs(props);

const { closeDialog, defaultNotes, openDialog, stateUpdated, submitting, trySubmit } = useHistoryEventsForm();

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
    :prompt-on-close="stateUpdated"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <HistoryEventForm
      :group-header="groupHeader"
      :editable-item="editableItem"
      :next-sequence="nextSequence"
      :default-notes="defaultNotes"
      :group-events="groupEvents"
    />
  </BigDialog>
</template>
