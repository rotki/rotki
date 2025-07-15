<script setup lang="ts">
import type { CalendarEvent } from '@/types/history/calendar';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import CalendarForm from '@/components/calendar/CalendarForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { useCalendarApi } from '@/composables/history/calendar';
import { useMessageStore } from '@/store/message';
import { ApiValidationError } from '@/types/api/errors';

const modelValue = defineModel<CalendarEvent | undefined>({ required: true });

const props = defineProps<{
  editMode: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'delete'): void;
  (e: 'refresh'): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const submitting = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof CalendarForm>>('form');
const stateUpdated = ref(false);

const { setMessage } = useMessageStore();
const { addCalendarEvent, editCalendarEvent } = useCalendarApi();

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  const editMode = props.editMode;
  const payload = {
    ...data,
  };

  set(submitting, true);
  let success;
  try {
    const result = !editMode
      ? await addCalendarEvent(omit(payload, ['identifier']))
      : await editCalendarEvent(payload);

    const eventId = result.entryId;
    if (isDefined(eventId)) {
      formRef?.reset();
      await formRef?.saveTemporaryReminder(eventId);
    }

    success = true;
  }
  catch (error: any) {
    success = false;
    const errorTitle = editMode ? t('calendar.edit_error') : t('calendar.add_error');

    let errors = error.message;
    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(payload);

    if (typeof errors === 'string') {
      setMessage({
        description: errors,
        success: false,
        title: errorTitle,
      });
    }
    else {
      set(errorMessages, errors);
    }
  }

  set(submitting, false);
  if (success) {
    set(modelValue, undefined);
    emit('refresh');
  }
  return success;
}

const dialogTitle = computed<string>(() =>
  props.editMode ? t('calendar.dialog.edit.title') : t('calendar.dialog.add.title'),
);
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
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
        @click="emit('delete')"
      >
        {{ t('calendar.delete_event') }}
      </RuiButton>
    </template>
  </BigDialog>
</template>
