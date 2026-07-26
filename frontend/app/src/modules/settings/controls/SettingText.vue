<script setup lang="ts">
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import useVuelidate, { type ValidationArgs } from '@vuelidate/core';
import { helpers, maxLength as maxLengthRule, required as requiredRule } from '@vuelidate/validators';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Generic owning component for a string setting. Bakes in optional `required` + `maxLength` validation
 * from props and persists through `useSettingModel` (debounced while typing, immediate on reset). Renders
 * only the field + optional reset button; put it inside a `SettingsItem` for the header. For settings
 * with bespoke validation (format directives, custom checks), pass a full vuelidate `rules` object keyed
 * under `value` to replace the baked rules.
 */
defineOptions({ inheritAttrs: false });

const {
  setting,
  label = '',
  default: defaultValue,
  required = false,
  maxLength,
  rules,
  transform = (value: string): string => value,
  successMessage = '',
  errorMessage = '',
  debounce = 1500,
} = defineProps<{
  setting: WritableSettingKeyOf<string>;
  label?: string;
  /** When provided, shows a reset-to-default button that writes this value immediately. */
  default?: string;
  required?: boolean;
  maxLength?: number;
  /** Escape hatch: a vuelidate rules object keyed under `value`, replacing the baked required/maxLength. */
  rules?: ValidationArgs;
  /** Maps the field string to the stored value. Defaults to identity. */
  transform?: (value: string) => string;
  /** Static text, or a callback given the persisted value. */
  successMessage?: string | ((value: string) => string);
  errorMessage?: string;
  debounce?: number;
}>();

const emit = defineEmits<{
  /** Fired after a successful persist, mirroring the old `SettingsOption` `@finished` hook. */
  updated: [value: string];
}>();

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, flush, model, success: writeSuccess } = useSettingModel(setting, { debounce });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

const input = ref<string>(get(model));

const bakedRules = computed<ValidationArgs>(() => {
  const valueRules: Record<string, ReturnType<typeof helpers.withMessage>> = {};
  if (required)
    valueRules.required = helpers.withMessage(t('settings.validation.text.non_empty'), requiredRule);

  if (maxLength !== undefined)
    valueRules.maxLength = helpers.withMessage(t('settings.validation.text.max_length', { max: maxLength }), maxLengthRule(maxLength));

  return { value: valueRules };
});

const activeRules = computed<ValidationArgs>(() => rules ?? get(bakedRules));

const states = computed(() => ({ value: get(input) }));

const v$ = useVuelidate(activeRules, states, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const hasDefault = computed<boolean>(() => defaultValue !== undefined);

// Reflect external changes into the field, but ignore the echo of our own writes (same string).
watch(model, (value) => {
  if (value !== get(input))
    set(input, value);
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

  set(input, defaultValue);
  set(model, transform(defaultValue));
  await flush();
}
</script>

<template>
  <div class="flex items-start w-full">
    <RuiTextField
      v-bind="$attrs"
      v-model="input"
      type="text"
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
