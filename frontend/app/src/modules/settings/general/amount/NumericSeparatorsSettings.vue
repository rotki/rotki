<script setup lang="ts">
import type { ZodType } from 'zod';
import { useForm } from '@/modules/core/form/use-form';
import { numericSeparatorsSchema, type NumericSeparatorsState } from '@/modules/settings/general/amount/numeric-separators';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const { t } = useI18n({ useScope: 'global' });

const { error: thousandWriteError, model: thousandModel, success: thousandWriteSuccess } = useSettingModel('thousandSeparator', { debounce: 1500 });
const { error: decimalWriteError, model: decimalModel, success: decimalWriteSuccess } = useSettingModel('decimalSeparator', { debounce: 1500 });
const { clearAll: clearThousandMessages, error: thousandError, setError: setThousandError, setSuccess: setThousandSuccess, success: thousandSuccess } = useClearableMessages();
const { clearAll: clearDecimalMessages, error: decimalError, setError: setDecimalError, setSuccess: setDecimalSuccess, success: decimalSuccess } = useClearableMessages();

const schema = computed<ZodType>(() => numericSeparatorsSchema({
  decimal: {
    empty: t('general_settings.decimal_separator.validation.empty'),
    numeric: t('general_settings.decimal_separator.validation.cannot_be_numeric_character'),
    sameAsOther: t('general_settings.decimal_separator.validation.cannot_be_the_same'),
    singleCharacter: t('general_settings.decimal_separator.validation.single_character'),
  },
  thousand: {
    empty: t('general_settings.thousand_separator.validation.empty'),
    numeric: t('general_settings.thousand_separator.validation.cannot_be_numeric_character'),
    sameAsOther: t('general_settings.thousand_separator.validation.cannot_be_the_same'),
    singleCharacter: t('general_settings.thousand_separator.validation.single_character'),
  },
}));

/**
 * One form for both separators. Submitting writes both models: the pair only persists when it
 * parses as a pair, which is what stops a rejected draft of one field from being the value the
 * other is compared against. The write of the unchanged field is a no-op in `useSettingModel`.
 */
const form = useForm<NumericSeparatorsState, NumericSeparatorsState>({
  initial: (): NumericSeparatorsState => ({ decimal: get(decimalModel), thousand: get(thousandModel) }),
  schema,
  submit: async (payload: NumericSeparatorsState): Promise<{ success: boolean }> => {
    set(thousandModel, payload.thousand);
    set(decimalModel, payload.decimal);
    return Promise.resolve({ success: true });
  },
  transform: (state): NumericSeparatorsState => ({ decimal: state.decimal, thousand: state.thousand }),
});

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

async function onThousandInput(value: string): Promise<void> {
  clearThousandMessages();
  form.state.thousand = value;
  await form.submit();
}

async function onDecimalInput(value: string): Promise<void> {
  clearDecimalMessages();
  form.state.decimal = value;
  await form.submit();
}

// Reflect external changes into the fields, but ignore the echo of our own writes (same string).
watch(thousandModel, (value) => {
  if (value !== form.state.thousand)
    form.state.thousand = value;
});

watch(decimalModel, (value) => {
  if (value !== form.state.decimal)
    form.state.decimal = value;
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
    v-model="form.state.thousand"
    variant="outlined"
    color="primary"
    data-cy="thousand-separator-input"
    :label="t('general_settings.amount.label.thousand_separator')"
    type="text"
    :success-messages="thousandSuccess"
    :error-messages="thousandError || form.errors('thousand')"
    @update:model-value="onThousandInput($event)"
  />

  <RuiTextField
    v-model="form.state.decimal"
    variant="outlined"
    color="primary"
    data-cy="decimal-separator-input"
    :label="t('general_settings.amount.label.decimal_separator')"
    type="text"
    :success-messages="decimalSuccess"
    :error-messages="decimalError || form.errors('decimal')"
    @update:model-value="onDecimalInput($event)"
  />
</template>
