<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, maxLength, required } from '@vuelidate/validators';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { Defaults } from '@/data/defaults';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { toMessages } from '@/utils/validation';

const DEFAULT_DELIMITER = Defaults.DEFAULT_CSV_EXPORT_DELIMITER;
const csvExportDelimiter = ref<string>(DEFAULT_DELIMITER);
const { csvExportDelimiter: delimiter } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n({ useScope: 'global' });

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

function reset(update: (value: string) => void) {
  update(DEFAULT_DELIMITER);
  set(csvExportDelimiter, DEFAULT_DELIMITER);
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
    <div class="flex items-start w-full">
      <RuiTextField
        v-model="csvExportDelimiter"
        variant="outlined"
        color="primary"
        maxlength="1"
        class="w-full"
        :label="t('general_settings.labels.csv_delimiter')"
        type="text"
        :success-messages="success"
        :error-messages="error || toMessages(v$.csvExportDelimiter)"
        @update:model-value="callIfCsvExportDelimiterValid($event, updateImmediate)"
      />

      <RuiButton
        class="mt-1 ml-2"
        variant="text"
        icon
        @click="reset(updateImmediate)"
      >
        <RuiIcon name="lu-history" />
      </RuiButton>
    </div>
  </SettingsOption>
</template>
