<script setup lang="ts">
import type { CalendarEvent } from '@/modules/calendar/types';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import CalendarForm from '@/modules/calendar/CalendarForm.vue';
import { useCalendarApi } from '@/modules/calendar/use-calendar-api';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<CalendarEvent | undefined>({ required: true });

const { editMode } = defineProps<{
  editMode: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  delete: [];
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const submitting = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof CalendarForm>>('form');
const stateUpdated = ref(false);

const { setMessage } = useMessageStore();
const { addCalendarEvent, editCalendarEvent } = useCalendarApi();

type CalendarFormInstance = InstanceType<typeof CalendarForm> | null | undefined;

async function persistEvent(payload: CalendarEvent, formRef: CalendarFormInstance): Promise<void> {
  const result = editMode
    ? await editCalendarEvent(payload)
    : await addCalendarEvent(omit(payload, ['identifier']));

  // The reminders are held in the form until here, because one can only be attached to an event
  // that has an id, and because a row must not reach the server before the user has saved.
  const eventId = result.entryId;
  if (isDefined(eventId)) {
    formRef?.reset();
    await formRef?.saveReminders(eventId);
  }
}

/**
 * Field-level errors go back to the form so it can mark the offending inputs; anything else has no
 * field to attach to and is surfaced as a message.
 */
function reportSaveFailure(error: unknown, payload: CalendarEvent): void {
  const errors: string | ValidationErrors = error instanceof ApiValidationError
    ? error.getValidationErrors(payload)
    : getErrorMessage(error);

  if (typeof errors !== 'string') {
    set(errorMessages, errors);
    return;
  }

  setMessage({
    description: errors,
    success: false,
    title: editMode ? t('calendar.edit_error') : t('calendar.add_error'),
  });
}

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const payload = { ...get(modelValue) };

  set(submitting, true);
  let success = true;
  try {
    await persistEvent(payload, formRef);
  }
  catch (error: unknown) {
    success = false;
    reportSaveFailure(error, payload);
  }
  set(submitting, false);

  if (success) {
    set(modelValue, undefined);
    emit('refresh');
  }

  return success;
}

const dialogTitle = computed<string>(() =>
  editMode ? t('calendar.dialog.edit.title') : t('calendar.dialog.add.title'),
);
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :action="{ disabled: loading, primary: t('common.actions.save') }"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <CalendarForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode"
    />

    <template #left-buttons>
      <RuiButton
        v-if="editMode"
        color="error"
        data-testid="calendar-form-delete"
        @click="emit('delete')"
      >
        {{ t('calendar.delete_event') }}
      </RuiButton>
    </template>
  </BigDialog>
</template>
