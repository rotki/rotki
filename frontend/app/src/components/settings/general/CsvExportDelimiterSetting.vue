<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, maxLength, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

const csvExportDelimiter = ref<string>('');
const { csvExportDelimiter: delimiter } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const rules = {
  csvExportDelimiter: {
    required: helpers.withMessage(t('general_settings.validation.csv_delimiter.empty'), required),
    singleCharacter: helpers.withMessage(
      t('general_settings.validation.csv_delimiter.single_character'),
      maxLength(1),
    ),
  },
};

const v$ = useVuelidate(rules, { csvExportDelimiter }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function callIfCsvExportDelimiterValid(value: string, method: (value: string) => void) {
  const validator = get(v$);
  callIfValid(value, method, () => validator.csvExportDelimiter.$error);
}

function successMessage(delimiterValue: string) {
  return t('general_settings.validation.csv_delimiter.success', {
    delimiter: delimiterValue,
  });
}

onMounted(() => {
  set(csvExportDelimiter, get(delimiter));
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="csvExportDelimiter"
    :error-message="t('general_settings.validation.csv_delimiter.error')"
    :success-message="successMessage"
  >
    <RuiTextField
      v-model="csvExportDelimiter"
      variant="outlined"
      color="primary"
      maxlength="1"
      :label="t('general_settings.labels.csv_delimiter')"
      type="text"
      :success-messages="success"
      :error-messages="error || toMessages(v$.csvExportDelimiter)"
      @update:model-value="callIfCsvExportDelimiterValid($event, updateImmediate)"
    />
  </SettingsOption>
</template>
