<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, not, numeric, sameAs } from '@vuelidate/validators';
import { useValidation } from '@/modules/core/common/use-validation';
import { isSingleVisualCharacter, toMessages } from '@/modules/core/common/validation/validation';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const { t } = useI18n({ useScope: 'global' });

const { error: thousandWriteError, model: thousandModel, success: thousandWriteSuccess } = useSettingModel('thousandSeparator', { debounce: 1500 });
const { error: decimalWriteError, model: decimalModel, success: decimalWriteSuccess } = useSettingModel('decimalSeparator', { debounce: 1500 });
const { clearAll: clearThousandMessages, error: thousandError, setError: setThousandError, setSuccess: setThousandSuccess, success: thousandSuccess } = useClearableMessages();
const { clearAll: clearDecimalMessages, error: decimalError, setError: setDecimalError, setSuccess: setDecimalSuccess, success: decimalSuccess } = useClearableMessages();

const thousandSeparator = ref<string>(get(thousandModel));
const decimalSeparator = ref<string>(get(decimalModel));

// Custom validator that allows spaces but not empty strings
const notEmpty = (value: any): boolean => value?.length > 0;

// Custom validator for single visual character
const singleVisualChar = (value: any): boolean => isSingleVisualCharacter(value);

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

function onThousandInput(value: string): void {
  clearThousandMessages();
  const validator = get(v$);
  callIfValid(value, (separator: string) => {
    set(thousandModel, separator);
  }, () => validator.thousandSeparator.$error);
}

function onDecimalInput(value: string): void {
  clearDecimalMessages();
  const validator = get(v$);
  callIfValid(value, (separator: string) => {
    set(decimalModel, separator);
  }, () => validator.decimalSeparator.$error);
}

function thousandsSuccessMessage(thousandSeparator: string): string {
  return t('general_settings.validation.thousand_separator.success', {
    thousandSeparator,
  });
}

function decimalsSuccessMessage(decimalSeparator: string): string {
  return t('general_settings.validation.decimal_separator.success', {
    decimalSeparator,
  });
}

watch(thousandModel, (value) => {
  if (value !== get(thousandSeparator))
    set(thousandSeparator, value);
});

watch(decimalModel, (value) => {
  if (value !== get(decimalSeparator))
    set(decimalSeparator, value);
});

watch(thousandWriteSuccess, (saved) => {
  if (saved)
    setThousandSuccess(thousandsSuccessMessage(get(thousandModel)), true);
});

watch(thousandWriteError, (message) => {
  if (message)
    setThousandError(`${t('general_settings.validation.thousand_separator.error')}: ${message}`, true);
});

watch(decimalWriteSuccess, (saved) => {
  if (saved)
    setDecimalSuccess(decimalsSuccessMessage(get(decimalModel)), true);
});

watch(decimalWriteError, (message) => {
  if (message)
    setDecimalError(`${t('general_settings.validation.decimal_separator.error')}: ${message}`, true);
});
</script>

<template>
  <RuiTextField
    v-model="thousandSeparator"
    variant="outlined"
    color="primary"
    data-cy="thousand-separator-input"
    :label="t('general_settings.amount.label.thousand_separator')"
    type="text"
    :success-messages="thousandSuccess"
    :error-messages="thousandError || toMessages(v$.thousandSeparator)"
    @update:model-value="onThousandInput($event)"
  />

  <RuiTextField
    v-model="decimalSeparator"
    variant="outlined"
    color="primary"
    data-cy="decimal-separator-input"
    :label="t('general_settings.amount.label.decimal_separator')"
    type="text"
    :success-messages="decimalSuccess"
    :error-messages="decimalError || toMessages(v$.decimalSeparator)"
    @update:model-value="onDecimalInput($event)"
  />
</template>
