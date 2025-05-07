<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

const floatingPrecision = ref<string>('0');
const maxFloatingPrecision = 8;
const { t } = useI18n({ useScope: 'global' });
const rules = {
  floatingPrecision: {
    required: helpers.withMessage(t('general_settings.validation.floating_precision.non_empty'), required),
  },
};

const { floatingPrecision: current } = storeToRefs(useGeneralSettingsStore());
const v$ = useVuelidate(rules, { floatingPrecision }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function resetFloatingPrecision() {
  set(floatingPrecision, get(current).toString());
}

const transform = (value?: string) => (value ? Number.parseInt(value) : value);

function errorMessage(precision: string) {
  return t('general_settings.validation.floating_precision.error', {
    precision,
  });
}

function successMessage(precision: string) {
  return t('general_settings.validation.floating_precision.success', {
    precision,
  });
}

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
    <RuiTextField
      v-model="floatingPrecision"
      variant="outlined"
      color="primary"
      min="1"
      :max="maxFloatingPrecision"
      data-cy="floating-precision-settings"
      :label="t('general_settings.amount.labels.floating_precision')"
      type="number"
      :success-messages="success"
      :error-messages="error || toMessages(v$.floatingPrecision)"
      @update:model-value="callIfValid($event, update)"
    />
  </SettingsOption>
</template>
