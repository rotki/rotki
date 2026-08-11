<script setup lang="ts">
import type { ZodType } from 'zod';
import { startPromise } from '@shared/utils';
import { useForm } from '@/modules/core/form/use-form';
import { numericSeparatorsSchema, type NumericSeparatorsState } from '@/modules/settings/general/amount/numeric-separators';
import { useSettingsWriter } from '@/modules/settings/settings-writer';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSetting } from '@/modules/settings/use-setting';

/** Matches the debounce the shared text setting controls persist with. */
const PERSIST_DEBOUNCE = 1500;

const { t } = useI18n({ useScope: 'global' });

const { writeMany } = useSettingsWriter();
const thousandSource = useSetting('thousandSeparator');
const decimalSource = useSetting('decimalSeparator');
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
 * One form for both separators: the pair only persists when it parses as a pair, which is what stops
 * a rejected draft of one field from being the value the other is compared against. Persistence is
 * driven from the input handlers rather than `submit`, so the write can be debounced without the
 * form and the writer having to reference each other.
 */
const form = useForm<NumericSeparatorsState, NumericSeparatorsState>({
  initial: (): NumericSeparatorsState => ({ decimal: get(decimalSource), thousand: get(thousandSource) }),
  schema,
  // Unused: `submitPair` below owns the write so it can be debounced. The core requires a submit.
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): NumericSeparatorsState => ({ decimal: state.decimal, thousand: state.thousand }),
});

/**
 * Persists the pair in ONE patch. Two independent writes cannot be used here: each snapshots the
 * whole frontend-settings blob before its request and merges only its own key, so two in flight at
 * once both send the other key's pre-edit value and the later response wins. Swapping the separators
 * that way put two identical characters on the backend while the merged local repo looked correct.
 */
async function persist(state: NumericSeparatorsState): Promise<void> {
  if (state.thousand === get(thousandSource) && state.decimal === get(decimalSource))
    return;

  const status = await writeMany({
    decimalSeparator: state.decimal,
    thousandSeparator: state.thousand,
  });

  if (status.success) {
    setThousandSuccess(thousandsSuccessMessage(state.thousand), true);
    setDecimalSuccess(decimalsSuccessMessage(state.decimal), true);
    return;
  }

  // Keep the fields showing what is stored rather than a pair that was rejected.
  form.state.thousand = get(thousandSource);
  form.state.decimal = get(decimalSource);
  setThousandError(`${t('general_settings.validation.thousand_separator.error')}: ${status.message ?? ''}`, true);
  setDecimalError(`${t('general_settings.validation.decimal_separator.error')}: ${status.message ?? ''}`, true);
}

const schedulePersist = useDebounceFn(persist, PERSIST_DEBOUNCE);

/** Reveals the pair's errors and schedules the write only when it parses, as `callIfValid` did. */
function submitPair(): void {
  if (form.validate())
    startPromise(schedulePersist({ decimal: form.state.decimal, thousand: form.state.thousand }));
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

function onThousandInput(value: string): void {
  clearThousandMessages();
  form.state.thousand = value;
  submitPair();
}

function onDecimalInput(value: string): void {
  clearDecimalMessages();
  form.state.decimal = value;
  submitPair();
}

// Reflect external changes into the fields, but ignore the echo of our own writes (same string).
watch(thousandSource, (value) => {
  if (value !== form.state.thousand)
    form.state.thousand = value;
});

watch(decimalSource, (value) => {
  if (value !== form.state.decimal)
    form.state.decimal = value;
});
</script>

<template>
  <RuiTextField
    v-model="form.state.thousand"
    variant="outlined"
    color="primary"
    data-testid="thousand-separator-input"
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
    data-testid="decimal-separator-input"
    :label="t('general_settings.amount.label.decimal_separator')"
    type="text"
    :success-messages="decimalSuccess"
    :error-messages="decimalError || form.errors('decimal')"
    @update:model-value="onDecimalInput($event)"
  />
</template>
