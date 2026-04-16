<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import DateInputFormatSelector from '@/modules/settings/general/DateInputFormatSelector.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const dateInputFormat = ref<string>('');
const { dateInputFormat: inputFormat } = storeToRefs(useFrontendSettingsStore());

const { t } = useI18n({ useScope: 'global' });

function containsValidDirectives(v: string) {
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

function resetDateInputFormat() {
  set(dateInputFormat, get(inputFormat));
}

function successMessage(dateFormat: string) {
  return t('general_settings.validation.date_input_format.success', {
    dateFormat,
  });
}

onMounted(() => {
  resetDateInputFormat();
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="dateInputFormat"
    frontend-setting
    :error-message="t('general_settings.validation.date_input_format.error')"
    :success-message="successMessage"
    @finished="resetDateInputFormat()"
  >
    <DateInputFormatSelector
      v-model="dateInputFormat"
      :label="t('general_settings.labels.date_input_format')"
      :success-messages="success ? [success] : []"
      :error-messages="error ? [error] : toMessages(v$.dateInputFormat)"
      @update:model-value="callIfValid($event, updateImmediate)"
    />
  </SettingsOption>
</template>
