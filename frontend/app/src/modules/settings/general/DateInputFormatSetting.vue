<script setup lang="ts">
import type { ZodType } from 'zod';
import { useForm } from '@/modules/core/form/use-form';
import { SETTING_FIELD, type SettingFieldState } from '@/modules/settings/controls/setting-field-schemas';
import { dateFormatSchema } from '@/modules/settings/general/date-format-schema';
import DateInputFormatSelector from '@/modules/settings/general/DateInputFormatSelector.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, model, success: writeSuccess } = useSettingModel('dateInputFormat', { debounce: 0 });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

const schema = computed<ZodType>(() => dateFormatSchema({
  empty: t('general_settings.date_display.validation.empty'),
  invalid: t('general_settings.date_display.validation.invalid'),
}));

/** Submitting is the persist: the core runs it only when the field parses, as `callIfValid` did. */
const form = useForm<SettingFieldState, SettingFieldState>({
  initial: (): SettingFieldState => ({ value: get(model) }),
  schema,
  submit: async (payload: SettingFieldState): Promise<{ success: boolean }> => {
    set(model, payload.value);
    return Promise.resolve({ success: true });
  },
  transform: (state): SettingFieldState => ({ value: state.value }),
});

function successMessage(dateFormat: string): string {
  return t('general_settings.validation.date_input_format.success', {
    dateFormat,
  });
}

async function onInput(value: string): Promise<void> {
  clearAll();
  form.state.value = value;
  await form.submit();
}

// Reflect external changes into the field, but ignore the echo of our own writes (same string).
watch(model, (value) => {
  if (value !== form.state.value)
    form.state.value = value;
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess(successMessage(get(model)), true);
});

watch(writeError, (message) => {
  if (message)
    setError(`${t('general_settings.validation.date_input_format.error')}: ${message}`, true);
});
</script>

<template>
  <DateInputFormatSelector
    v-model="form.state.value"
    :label="t('general_settings.labels.date_input_format')"
    :success-messages="success ? [success] : []"
    :error-messages="error ? [error] : form.errors(SETTING_FIELD)"
    @update:model-value="onInput($event)"
  />
</template>
