<template>
  <settings-option
    #default="{ error, success, update }"
    setting="dateInputFormat"
    frontend-setting
    :error-message="$tc('general_settings.validation.date_input_format.error')"
    :success-message="
      dateFormat =>
        $tc('general_settings.validation.date_input_format.success', 0, {
          dateFormat
        })
    "
    @finished="resetDateInputFormat"
  >
    <date-input-format-selector
      v-model="dateInputFormat"
      :label="$t('general_settings.labels.date_input_format')"
      class="pt-4 general-settings__fields__date-input-format"
      :success-messages="success"
      :error-messages="error || v$.dateInputFormat.$errors.map(e => e.$message)"
      @change="callIfValid($event, update)"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useValidation } from '@/composables/validation';
import { displayDateFormatter } from '@/data/date_formatter';
import i18n from '@/i18n';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const dateInputFormat = ref<string>('');
const { dateInputFormat: inputFormat } = storeToRefs(
  useFrontendSettingsStore()
);

const containsValidDirectives = (v: string) =>
  displayDateFormatter.containsValidDirectives(v);

const rules = {
  dateInputFormat: {
    required: helpers.withMessage(
      i18n.t('general_settings.date_display.validation.empty').toString(),
      required
    ),
    containsValidDirectives: helpers.withMessage(
      i18n.t('general_settings.date_display.validation.invalid').toString(),
      containsValidDirectives
    )
  }
};

const v$ = useVuelidate(rules, { dateInputFormat }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const resetDateInputFormat = () => {
  set(dateInputFormat, get(inputFormat));
};

onMounted(() => {
  resetDateInputFormat();
});
</script>
