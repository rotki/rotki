<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
import DateInputFormatSelector from '@/modules/settings/general/DateInputFormatSelector.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, model, success: writeSuccess } = useSettingModel('dateInputFormat', { debounce: 0 });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

const dateInputFormat = ref<string>(get(model));

function containsValidDirectives(v: string): boolean {
  return displayDateFormatter.containsValidDirectives(v);
}

const rules = {
  dateInputFormat: {
    containsValidDirectives: helpers.withMessage(
      t('general_settings.date_display.validation.invalid'),
      containsValidDirectives,
    ),
    required: helpers.withMessage(t('general_settings.date_display.validation.empty'), required),
  },
};

const v$ = useVuelidate(rules, { dateInputFormat }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function successMessage(dateFormat: string): string {
  return t('general_settings.validation.date_input_format.success', {
    dateFormat,
  });
}

function onInput(value: string): void {
  clearAll();
  callIfValid(value, (format: string) => {
    set(model, format);
  });
}

watch(model, (value) => {
  if (value !== get(dateInputFormat))
    set(dateInputFormat, value);
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
    v-model="dateInputFormat"
    :label="t('general_settings.labels.date_input_format')"
    :success-messages="success ? [success] : []"
    :error-messages="error ? [error] : toMessages(v$.dateInputFormat)"
    @update:model-value="onInput($event)"
  />
</template>
