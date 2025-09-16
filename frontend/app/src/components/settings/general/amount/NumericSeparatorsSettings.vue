<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, not, numeric, sameAs } from '@vuelidate/validators';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { isSingleVisualCharacter, toMessages } from '@/utils/validation';

const thousandSeparator = ref<string>('');
const decimalSeparator = ref<string>('');

const { decimalSeparator: decimals, thousandSeparator: thousands } = storeToRefs(useFrontendSettingsStore());

const { t } = useI18n({ useScope: 'global' });

// Custom validator that allows spaces but not empty strings
const notEmpty = (value: any) => value?.length > 0;

// Custom validator for single visual character
const singleVisualChar = (value: any) => isSingleVisualCharacter(value);

const rules = {
  decimalSeparator: {
    notANumber: helpers.withMessage(
      t('general_settings.decimal_separator.validation.cannot_be_numeric_character'),
      not(numeric),
    ),
    notEmpty: helpers.withMessage(t('general_settings.decimal_separator.validation.empty'), notEmpty),
    notTheSame: helpers.withMessage(
      t('general_settings.decimal_separator.validation.cannot_be_the_same'),
      not(sameAs(thousandSeparator)),
    ),
    singleChar: helpers.withMessage(
      t('general_settings.decimal_separator.validation.single_character'),
      singleVisualChar,
    ),
  },
  thousandSeparator: {
    notANumber: helpers.withMessage(
      t('general_settings.thousand_separator.validation.cannot_be_numeric_character'),
      not(numeric),
    ),
    notEmpty: helpers.withMessage(t('general_settings.thousand_separator.validation.empty'), notEmpty),
    notTheSame: helpers.withMessage(
      t('general_settings.thousand_separator.validation.cannot_be_the_same'),
      not(sameAs(decimalSeparator)),
    ),
    singleChar: helpers.withMessage(
      t('general_settings.thousand_separator.validation.single_character'),
      singleVisualChar,
    ),
  },
};

const v$ = useVuelidate(rules, { decimalSeparator, thousandSeparator }, { $autoDirty: true });

const { callIfValid } = useValidation(v$);

function callIfThousandsValid(value: string, method: (value: string) => void) {
  const validator = get(v$);
  callIfValid(value, method, () => validator.thousandSeparator.$error);
}

function callIfDecimalsValid(value: string, method: (value: string) => void) {
  const validator = get(v$);
  callIfValid(value, method, () => validator.decimalSeparator.$error);
}

function thousandsSuccessMessage(thousandSeparator: string) {
  return t('general_settings.validation.thousand_separator.success', {
    thousandSeparator,
  });
}

function decimalsSuccessMessage(decimalSeparator: string) {
  return t('general_settings.validation.decimal_separator.success', {
    decimalSeparator,
  });
}

onMounted(() => {
  set(thousandSeparator, get(thousands));
  set(decimalSeparator, get(decimals));
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="thousandSeparator"
    frontend-setting
    :error-message="t('general_settings.validation.thousand_separator.error')"
    :success-message="thousandsSuccessMessage"
  >
    <RuiTextField
      v-model="thousandSeparator"
      variant="outlined"
      color="primary"
      data-cy="thousand-separator-input"
      :label="t('general_settings.amount.label.thousand_separator')"
      type="text"
      :success-messages="success"
      :error-messages="error || toMessages(v$.thousandSeparator)"
      @update:model-value="callIfThousandsValid($event, update)"
    />
  </SettingsOption>

  <SettingsOption
    #default="{ error, success, update }"
    setting="decimalSeparator"
    frontend-setting
    :error-message="t('general_settings.validation.decimal_separator.error')"
    :success-message="decimalsSuccessMessage"
  >
    <RuiTextField
      v-model="decimalSeparator"
      variant="outlined"
      color="primary"
      data-cy="decimal-separator-input"
      :label="t('general_settings.amount.label.decimal_separator')"
      type="text"
      :success-messages="success"
      :error-messages="error || toMessages(v$.decimalSeparator)"
      @update:model-value="callIfDecimalsValid($event, update)"
    />
  </SettingsOption>
</template>
