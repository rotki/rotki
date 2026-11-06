<script setup lang="ts">
import type { CalendarEvent } from '@/modules/calendar/types';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import CalendarForm from '@/modules/calendar/CalendarForm.vue';
import { useCalendarApi } from '@/modules/calendar/use-calendar-api';
import { useSaveFailure } from '@/modules/core/form/use-save-failure';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';
import { useDeleteQuestion } from '@/modules/shell/components/row-delete-question';

const modelValue = defineModel<CalendarEvent | undefined>({ required: true });

const { editMode } = defineProps<{
  editMode: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const submitting = ref(false);
const form = useTemplateRef<InstanceType<typeof CalendarForm>>('form');
const stateUpdated = ref(false);
/** Asking, in the footer, whether to delete the event being edited. */
const confirmingDelete = ref<boolean>(false);
const deleting = ref<boolean>(false);
const deleteFailure = shallowRef<unknown>();

const { capture, clear, failure, modelFieldErrors } = useSaveFailure();
const { addCalendarEvent, deleteCalendarEvent, editCalendarEvent } = useCalendarApi();
const toDeleteQuestion = useDeleteQuestion();

type CalendarFormInstance = InstanceType<typeof CalendarForm> | null | undefined;

async function persistEvent(payload: CalendarEvent, formRef: CalendarFormInstance): Promise<void> {
  const result = editMode
    ? await editCalendarEvent(payload)
    : await addCalendarEvent(omit(payload, ['identifier']));

  const eventId = result.entryId;
  if (isDefined(eventId)) {
    formRef?.reset();
    await formRef?.saveReminders(eventId);
  }
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
  clear();
  set(deleteFailure, undefined);
  let success = true;
  try {
    await persistEvent(payload, formRef);
  }
  catch (error: unknown) {
    success = false;
    capture(error, payload);
  }
  set(submitting, false);

  if (success) {
    set(modelValue, undefined);
    emit('refresh');
  }

  return success;
}

/**
 * Deletes the event being edited, once the footer question is answered.
 *
 * @remarks
 * A failure stays in the dialog, above the form, the way a failed save does.
 */
async function deleteEvent(): Promise<void> {
  const item = get(modelValue);
  if (!item)
    return;

  set(deleting, true);
  clear();
  set(deleteFailure, undefined);
  try {
    await deleteCalendarEvent(item.identifier);
    set(modelValue, undefined);
    emit('refresh');
  }
  catch (error: unknown) {
    set(deleteFailure, error);
  }
  finally {
    set(deleting, false);
    set(confirmingDelete, false);
  }
}

const shownFailure = computed<unknown>(() => get(deleteFailure) ?? get(failure));

const failureTitle = computed<string>(() => {
  if (get(deleteFailure) !== undefined)
    return t('calendar.delete_error.title');
  return editMode ? t('calendar.edit_error') : t('calendar.add_error');
});

watch(() => get(modelValue)?.identifier, () => {
  set(confirmingDelete, false);
  set(deleteFailure, undefined);
});

const deleteQuestion = computed<ConfirmQuestion>(() => toDeleteQuestion({
  message: t('calendar.dialog.delete.message'),
}));

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
    :failure="shownFailure"
    :failure-title="failureTitle"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <CalendarForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="modelFieldErrors"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode"
    />

    <template
      v-if="confirmingDelete"
      #footer
    >
      <InlineConfirm
        class="w-full"
        :question="deleteQuestion"
        :loading="deleting"
        data-testid="calendar-form-delete-confirm"
        @cancel="confirmingDelete = false"
        @confirm="deleteEvent()"
      />
    </template>

    <template #left-buttons>
      <RuiButton
        v-if="editMode"
        color="error"
        data-testid="calendar-form-delete"
        @click="confirmingDelete = true"
      >
        {{ t('calendar.delete_event') }}
      </RuiButton>
    </template>
  </BigDialog>
</template>
