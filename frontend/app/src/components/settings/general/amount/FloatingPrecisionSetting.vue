<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

const floatingPrecision = ref<string>('0');
const maxFloatingPrecision = 8;
const { t } = useI18n();
const rules = {
  floatingPrecision: {
    required: helpers.withMessage(
      t('general_settings.validation.floating_precision.non_empty'),
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

const transform = (value?: string) => (value ? Number.parseInt(value) : value);
const errorMessage = (precision: string) =>
  t('general_settings.validation.floating_precision.error', {
    precision
  });
const successMessage = (precision: string) =>
  t('general_settings.validation.floating_precision.success', {
    precision
  });

onMounted(() => {
  resetFloatingPrecision();
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="uiFloatingPrecision"
    :transform="transform"
    :error-message="errorMessage"
    :success-message="successMessage"
    @finished="resetFloatingPrecision()"
  >
    <VTextField
      v-model="floatingPrecision"
      outlined
      min="1"
      :max="maxFloatingPrecision"
      class="general-settings__fields__floating-precision"
      :label="t('general_settings.amount.labels.floating_precision')"
      type="number"
      :success-messages="success"
      :error-messages="
        error || v$.floatingPrecision.$errors.map(e => e.$message)
      "
      @change="callIfValid($event, update)"
    />
  </SettingsOption>
</template>