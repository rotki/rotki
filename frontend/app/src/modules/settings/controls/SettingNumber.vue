<script setup lang="ts">
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import useVuelidate, { type ValidationArgs } from '@vuelidate/core';
import { between, helpers, maxValue, minValue, required as requiredRule } from '@vuelidate/validators';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Generic owning component for a numeric setting. Bakes in the common `required` + `between`/`min`/`max`
 * validation from props and persists through `useSettingModel` (debounced while typing, immediate on
 * reset). Renders only the field + optional reset button; put it inside a `SettingsItem` for the header.
 * For settings whose validation is not min/max/required (single-character, cross-field, custom formats),
 * pass a full vuelidate `rules` object keyed under `value` to replace the baked rules.
 */
defineOptions({ inheritAttrs: false });

const {
  setting,
  label = '',
  min,
  max,
  default: defaultValue,
  required = true,
  rules,
  transform = (value: string): number => Number.parseInt(value),
  successMessage = '',
  errorMessage = '',
  debounce = 1500,
  // eslint-disable-next-line vue/max-props -- a generic owning control needs the full setting/label/validation/message surface
} = defineProps<{
  setting: WritableSettingKeyOf<number>;
  label?: string;
  min?: number;
  max?: number;
  /** When provided, shows a reset-to-default button that writes this value immediately. */
  default?: number;
  required?: boolean;
  /** Escape hatch: a vuelidate rules object keyed under `value`, replacing the baked min/max/required. */
  rules?: ValidationArgs;
  /** Maps the field string to the stored number. Defaults to `Number.parseInt`; override for floats. */
  transform?: (value: string) => number;
  /** Static text, or a callback given the persisted value. */
  successMessage?: string | ((value: number) => string);
  errorMessage?: string;
  debounce?: number;
}>();

const emit = defineEmits<{
  /** Fired after a successful persist, mirroring the old `SettingsOption` `@finished` hook. */
  updated: [value: number];
}>();

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, flush, model, success: writeSuccess } = useSettingModel(setting, { debounce });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

const input = ref<string>(String(get(model)));

const bakedRules = computed<ValidationArgs>(() => {
  const valueRules: Record<string, ReturnType<typeof helpers.withMessage>> = {};
  if (required)
    valueRules.required = helpers.withMessage(t('settings.validation.number.non_empty'), requiredRule);

  if (min !== undefined && max !== undefined)
    valueRules.between = helpers.withMessage(t('settings.validation.number.between', { max, min }), between(min, max));
  else if (min !== undefined)
    valueRules.min = helpers.withMessage(t('settings.validation.number.min', { min }), minValue(min));
  else if (max !== undefined)
    valueRules.max = helpers.withMessage(t('settings.validation.number.max', { max }), maxValue(max));

  return { value: valueRules };
});

const activeRules = computed<ValidationArgs>(() => rules ?? get(bakedRules));

const states = computed(() => ({ value: get(input) }));

const v$ = useVuelidate(activeRules, states, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const hasDefault = computed<boolean>(() => defaultValue !== undefined);

// Reflect external changes into the field, but ignore the echo of our own writes (same string).
watch(model, (value) => {
  if (String(value) !== get(input))
    set(input, String(value));
});

watch(writeSuccess, (saved) => {
  if (saved) {
    setSuccess(typeof successMessage === 'function' ? successMessage(get(model)) : successMessage, true);
    emit('updated', get(model));
  }
});

watch(writeError, (message) => {
  if (message)
    setError(errorMessage ? `${errorMessage}: ${message}` : message, true);
});

function persistValue(value: string): void {
  set(model, transform(value));
}

function onInput(value: string): void {
  clearAll();
  callIfValid(value, persistValue);
}

async function reset(): Promise<void> {
  if (defaultValue === undefined)
    return;

  set(input, String(defaultValue));
  set(model, transform(String(defaultValue)));
  await flush();
}
</script>

<template>
  <div class="flex items-start w-full">
    <RuiTextField
      v-bind="$attrs"
      v-model="input"
      type="number"
      variant="outlined"
      color="primary"
      class="w-full"
      :label="label"
      :success-messages="success"
      :error-messages="error || toMessages(v$.value)"
      @update:model-value="onInput($event)"
    />

    <SettingResetConfirmButton
      v-if="hasDefault"
      @confirm="reset()"
    />
  </div>
</template>
