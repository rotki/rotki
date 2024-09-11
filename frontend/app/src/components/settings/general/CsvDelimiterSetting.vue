<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, maxLength, required } from '@vuelidate/validators';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { toMessages } from '@/utils/validation';

const settingsStore = useFrontendSettingsStore();
const csvSeparator = computed(() => settingsStore.settings.csvSeparator);
const csvDelimiter = ref(get(csvSeparator));

const { t } = useI18n();

const rules = {
  csvDelimiter: {
    required: helpers.withMessage(t('general_settings.validation.csv_delimiter.empty'), required),
    singleCharacter: helpers.withMessage(
      t('general_settings.validation.csv_delimiter.single_character'),
      maxLength(1),
    ),
  },
};

const v$ = useVuelidate(rules, { csvDelimiter }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function resetCsvDelimiter() {
  set(csvDelimiter, get(csvSeparator));
}

function successMessage(delimiter: string) {
  return t('general_settings.validation.csv_delimiter.success', { delimiter });
}

onMounted(() => {
  resetCsvDelimiter();
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="csvSeparator"
    frontend-setting
    :error-message="t('general_settings.validation.csv_delimiter.error')"
    :success-message="successMessage"
    @finished="resetCsvDelimiter()"
  >
    <RuiTextField
      v-model="csvDelimiter"
      variant="outlined"
      color="primary"
      maxlength="1"
      class="general-settings__fields__csv-delimiter"
      :label="t('general_settings.labels.csv_delimiter')"
      :success-messages="success ? [success] : []"
      :error-messages="error ? [error] : toMessages(v$.csvDelimiter)"
      @update:model-value="callIfValid($event, updateImmediate)"
    />
  </SettingsOption>
</template>
