<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, not, numeric, required, sameAs } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

const thousandSeparator = ref<string>('');
const decimalSeparator = ref<string>('');

const { thousandSeparator: thousands, decimalSeparator: decimals } = storeToRefs(useFrontendSettingsStore());

const { t } = useI18n();

const rules = {
  thousandSeparator: {
    required: helpers.withMessage(t('general_settings.thousand_separator.validation.empty'), required),
    notANumber: helpers.withMessage(
      t('general_settings.thousand_separator.validation.cannot_be_numeric_character'),
      not(numeric),
    ),
    notTheSame: helpers.withMessage(
      t('general_settings.thousand_separator.validation.cannot_be_the_same'),
      not(sameAs(decimalSeparator)),
    ),
  },
  decimalSeparator: {
    required: helpers.withMessage(t('general_settings.decimal_separator.validation.empty'), required),
    notANumber: helpers.withMessage(
      t('general_settings.decimal_separator.validation.cannot_be_numeric_character'),
      not(numeric),
    ),
    notTheSame: helpers.withMessage(
      t('general_settings.decimal_separator.validation.cannot_be_the_same'),
      not(sameAs(thousandSeparator)),
    ),
  },
};

const v$ = useVuelidate(rules, { thousandSeparator, decimalSeparator }, { $autoDirty: true });

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
      maxlength="1"
      class="general-settings__fields__thousand-separator"
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
      maxlength="1"
      class="general-settings__fields__decimal-separator"
      :label="t('general_settings.amount.label.decimal_separator')"
      type="text"
      :success-messages="success"
      :error-messages="error || toMessages(v$.decimalSeparator)"
      @update:model-value="callIfDecimalsValid($event, update)"
    />
  </SettingsOption>
</template>
