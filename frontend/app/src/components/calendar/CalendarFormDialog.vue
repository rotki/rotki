<script setup lang="ts">
import { useCalendarEventForm } from '@/composables/calendar/form';
import CalendarForm from '@/components/calendar/CalendarForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import type { Dayjs } from 'dayjs';
import type { CalendarEvent } from '@/types/history/calendar';

const props = withDefaults(
  defineProps<{
    editableItem?: CalendarEvent;
    selectedDate: Dayjs;
    loading: boolean;
  }>(),
  {
    editableItem: undefined,
  },
);

const emit = defineEmits<{
  (e: 'delete'): void;
}>();

const { editableItem, loading } = toRefs(props);

const { closeDialog, openDialog, stateUpdated, submitting, trySubmit } = useCalendarEventForm();

const { t } = useI18n();

const title = computed<string>(() =>
  get(editableItem) ? t('calendar.dialog.edit.title') : t('calendar.dialog.add.title'),
);
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
    <CalendarForm
      :editable-item="editableItem"
      :selected-date="selectedDate"
    />

    <template #left-buttons>
      <RuiButton
        v-if="editableItem"
        color="error"
        @click="emit('delete')"
      >
        {{ t('calendar.delete_event') }}
      </RuiButton>
    </template>
  </BigDialog>
</template>
