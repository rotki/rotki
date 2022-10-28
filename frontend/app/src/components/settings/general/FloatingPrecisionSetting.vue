<template>
  <settings-option
    #default="{ error, success, update }"
    setting="uiFloatingPrecision"
    :transform="transform"
    :error-message="errorMessage"
    :success-message="successMessage"
    @finished="resetFloatingPrecision"
  >
    <v-text-field
      v-model="floatingPrecision"
      outlined
      min="1"
      :max="maxFloatingPrecision"
      class="general-settings__fields__floating-precision"
      :label="tc('general_settings.amount.labels.floating_precision')"
      type="number"
      :success-messages="success"
      :error-messages="
        error || v$.floatingPrecision.$errors.map(e => e.$message)
      "
      @change="callIfValid($event, update)"
    />
  </settings-option>
</template>

<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { useValidation } from '@/composables/validation';
import { useGeneralSettingsStore } from '@/store/settings/general';

const floatingPrecision = ref<string>('0');
const maxFloatingPrecision = 8;
const { tc } = useI18n();
const rules = {
  floatingPrecision: {
    required: helpers.withMessage(
      tc('general_settings.validation.floating_precision.non_empty'),
      required
    )
  }
};

const { floatingPrecision: current } = storeToRefs(useGeneralSettingsStore());
const v$ = useVuelidate(rules, { floatingPrecision }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const resetFloatingPrecision = () => {
  set(floatingPrecision, get(current).toString());
};

const transform = (value?: string) => (value ? parseInt(value) : value);
const errorMessage = (precision: string) =>
  tc('general_settings.validation.floating_precision.error', 0, {
    precision
  });
const successMessage = (precision: string) =>
  tc('general_settings.validation.floating_precision.success', 0, {
    precision
  });

onMounted(() => {
  resetFloatingPrecision();
});
</script>
