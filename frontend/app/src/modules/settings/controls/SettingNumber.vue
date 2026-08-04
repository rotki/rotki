<script setup lang="ts">
import type { ZodType } from 'zod';
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import { useForm } from '@/modules/core/form/use-form';
import { numberSettingSchema, SETTING_FIELD, type SettingFieldState } from '@/modules/settings/controls/setting-field-schemas';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Generic owning component for a numeric setting. Bakes in the common `required` + `between`/`min`/`max`
 * validation from props and persists through `useSettingModel` (debounced while typing, immediate on
 * reset). Renders only the field + optional reset button; put it inside a `SettingsItem` for the header.
 * For settings whose validation is not min/max/required (single-character, cross-field, custom formats),
 * pass a `schema` addressing the value under `SETTING_FIELD` to replace the baked one.
 */
defineOptions({ inheritAttrs: false });

const {
  setting,
  label = '',
  min,
  max,
  default: defaultValue,
  required = true,
  schema,
  transform = (value: string): number => Number.parseInt(value),
  successMessage = '',
  errorMessage = '',
  debounce = 1500,
} = defineProps<{
  setting: WritableSettingKeyOf<number>;
  label?: string;
  min?: number;
  max?: number;
  /** When provided, shows a reset-to-default button that writes this value immediately. */
  default?: number;
  required?: boolean;
  /** Escape hatch: a zod schema addressing the field under `SETTING_FIELD`, replacing the baked one. */
  schema?: ZodType;
  /** Maps the field string to the stored number. Defaults to `Number.parseInt`; override for floats. */
  transform?: (value: string) => number;
  /** Static text, or a callback given the persisted value. */
  successMessage?: string | ((value: number) => string);
  /** Static prefix, or a callback given the persisted value. Prefixed before the writer error. */
  errorMessage?: string | ((value: number) => string);
  debounce?: number;
}>();

const emit = defineEmits<{
  /** Fired after a successful persist, mirroring the old `SettingsOption` `@finished` hook. */
  updated: [value: number];
}>();

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, flush, model, success: writeSuccess } = useSettingModel(setting, { debounce });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

const bakedSchema = computed<ZodType>(() => numberSettingSchema({
  max,
  messages: {
    between: t('settings.validation.number.between', { max, min }),
    max: t('settings.validation.number.max', { max }),
    min: t('settings.validation.number.min', { min }),
    required: t('settings.validation.number.non_empty'),
  },
  min,
  required,
}));

const form = useForm<SettingFieldState, SettingFieldState>({
  initial: (): SettingFieldState => ({ value: String(get(model)) }),
  schema: () => schema ?? get(bakedSchema),
  submit: async (payload: SettingFieldState): Promise<{ success: boolean }> => {
    set(model, transform(payload.value));
    return Promise.resolve({ success: true });
  },
  transform: (state): SettingFieldState => ({ value: state.value }),
});

const hasDefault = computed<boolean>(() => defaultValue !== undefined);

// Reflect external changes into the field, but ignore the echo of our own writes (same string).
watch(model, (value) => {
  if (String(value) !== form.state.value)
    form.state.value = String(value);
});

watch(writeSuccess, (saved) => {
  if (saved) {
    setSuccess(typeof successMessage === 'function' ? successMessage(get(model)) : successMessage, true);
    emit('updated', get(model));
  }
});

watch(writeError, (message) => {
  if (message) {
    const prefix = typeof errorMessage === 'function' ? errorMessage(get(model)) : errorMessage;
    setError(prefix ? `${prefix}: ${message}` : message, true);
  }
});

/** Submitting is the persist: the core runs it only when the field parses, as `callIfValid` did. */
async function onInput(value: string): Promise<void> {
  clearAll();
  form.state.value = value;
  await form.submit();
}

async function reset(): Promise<void> {
  if (defaultValue === undefined)
    return;

  form.state.value = String(defaultValue);
  set(model, transform(String(defaultValue)));
  await flush();
}
</script>

<template>
  <div class="flex items-start w-full">
    <RuiTextField
      v-bind="$attrs"
      v-model="form.state.value"
      type="number"
      variant="outlined"
      color="primary"
      class="w-full"
      :label="label"
      :success-messages="success"
      :error-messages="error || form.errors(SETTING_FIELD)"
      @update:model-value="onInput($event)"
    />

    <SettingResetConfirmButton
      v-if="hasDefault"
      @confirm="reset()"
    />
  </div>
</template>
