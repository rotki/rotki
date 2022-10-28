<template>
  <settings-option
    #default="{ error, success, update }"
    setting="dateInputFormat"
    frontend-setting
    :error-message="tc('general_settings.validation.date_input_format.error')"
    :success-message="successMessage"
    @finished="resetDateInputFormat"
  >
    <date-input-format-selector
      v-model="dateInputFormat"
      :label="tc('general_settings.labels.date_input_format')"
      class="pt-4 general-settings__fields__date-input-format"
      :success-messages="success"
      :error-messages="error || v$.dateInputFormat.$errors.map(e => e.$message)"
      @change="callIfValid($event, update)"
    />
  </settings-option>
</template>

<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { useValidation } from '@/composables/validation';
import { displayDateFormatter } from '@/data/date_formatter';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const dateInputFormat = ref<string>('');
const { dateInputFormat: inputFormat } = storeToRefs(
  useFrontendSettingsStore()
);

const { tc } = useI18n();

const containsValidDirectives = (v: string) =>
  displayDateFormatter.containsValidDirectives(v);

const rules = {
  dateInputFormat: {
    required: helpers.withMessage(
      tc('general_settings.date_display.validation.empty'),
      required
    ),
    containsValidDirectives: helpers.withMessage(
      tc('general_settings.date_display.validation.invalid'),
      containsValidDirectives
    )
  }
};

const v$ = useVuelidate(rules, { dateInputFormat }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const resetDateInputFormat = () => {
  set(dateInputFormat, get(inputFormat));
};

const successMessage = (dateFormat: string) =>
  tc('general_settings.validation.date_input_format.success', 0, {
    dateFormat
  });

onMounted(() => {
  resetDateInputFormat();
});
</script>
