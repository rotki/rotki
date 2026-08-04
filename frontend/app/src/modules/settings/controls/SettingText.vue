<script setup lang="ts">
import type { ZodType } from 'zod';
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import { useForm } from '@/modules/core/form/use-form';
import { SETTING_FIELD, type SettingFieldState, textSettingSchema } from '@/modules/settings/controls/setting-field-schemas';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Generic owning component for a string setting. Bakes in optional `required` + `maxLength` validation
 * from props and persists through `useSettingModel` (debounced while typing, immediate on reset). Renders
 * only the field + optional reset button; put it inside a `SettingsItem` for the header. For settings
 * with bespoke validation (format directives, custom checks), pass a `schema` addressing the value
 * under `SETTING_FIELD` to replace the baked one.
 */
defineOptions({ inheritAttrs: false });

const {
  setting,
  label = '',
  default: defaultValue,
  required = false,
  maxLength,
  schema,
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
  /** Escape hatch: a zod schema addressing the field under `SETTING_FIELD`, replacing the baked one. */
  schema?: ZodType;
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

const bakedSchema = computed<ZodType>(() => textSettingSchema({
  maxLength,
  messages: {
    maxLength: t('settings.validation.text.max_length', { max: maxLength }),
    required: t('settings.validation.text.non_empty'),
  },
  required,
}));

const form = useForm<SettingFieldState, SettingFieldState>({
  initial: (): SettingFieldState => ({ value: get(model) }),
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
  if (value !== form.state.value)
    form.state.value = value;
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

/** Submitting is the persist: the core runs it only when the field parses, as `callIfValid` did. */
async function onInput(value: string): Promise<void> {
  clearAll();
  form.state.value = value;
  await form.submit();
}

async function reset(): Promise<void> {
  if (defaultValue === undefined)
    return;

  form.state.value = defaultValue;
  set(model, transform(defaultValue));
  await flush();
}
</script>

<template>
  <div class="flex items-start w-full">
    <RuiTextField
      v-bind="$attrs"
      v-model="form.state.value"
      type="text"
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
