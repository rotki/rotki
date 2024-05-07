<script setup lang="ts">
import { useCalendarEventForm } from '@/composables/calendar/form';
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

const { openDialog, submitting, closeDialog, trySubmit } = useCalendarEventForm();

const { t } = useI18n();

const title: ComputedRef<string> = computed(() =>
  get(editableItem)
    ? t('calendar.dialog.edit.title')
    : t('calendar.dialog.add.title'),
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
