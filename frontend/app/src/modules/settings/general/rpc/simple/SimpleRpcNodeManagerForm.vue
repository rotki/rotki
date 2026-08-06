<script setup lang="ts">
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { useForm } from '@/modules/core/form/use-form';
import { SETTING_FIELD, type SettingFieldState, textSettingSchema } from '@/modules/settings/controls/setting-field-schemas';

/**
 * The endpoint is one setting field, so it reuses the shared setting schema; the surrounding dialog
 * owns the persist, which is why `submit` here is a no-op.
 */
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const modelValue = defineModel<string>({ required: true });

const { disabled = false } = defineProps<{
  disabled?: boolean;
}>();

/** The key the dialog reports its save failures under, mapped onto the single form field. */
const ERROR_KEY = 'modelValue';

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => textSettingSchema({
  messages: {
    required: t('settings.validation.text.non_empty'),
  },
  required: true,
}));

const form = useForm<SettingFieldState, SettingFieldState>({
  initial: (): SettingFieldState => ({ value: get(modelValue) }),
  schema,
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): SettingFieldState => ({ value: state.value }),
});

function toMessages(value: ValidationErrors[string] | undefined): string[] {
  if (value === undefined)
    return [];

  return (Array.isArray(value) ? value : [value]).filter(message => message !== '');
}

watch(() => form.state.value, (value) => {
  set(modelValue, value);
  if (Object.keys(get(errors)).length > 0)
    set(errors, {});
});

// The dialog reseeds the field when it opens a different endpoint for editing.
watch(modelValue, (value) => {
  if (value !== form.state.value)
    form.state.value = value;
});

watch(errors, (value) => {
  form.setServerErrors({ [SETTING_FIELD]: toMessages(value[ERROR_KEY]) });
}, { deep: true, immediate: true });

watch(form.dirty, (dirty) => {
  set(stateUpdated, dirty);
});

// The dialog keeps its prompt-on-close flag across opens, so hand it back disarmed.
onUnmounted(() => {
  set(stateUpdated, false);
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <RuiTextField
    v-model="form.state.value"
    variant="outlined"
    color="primary"
    class="pt-2"
    :label="t('general_settings.labels.node_rpc_endpoint')"
    type="text"
    clearable
    :disabled="disabled"
    :error-messages="form.errors(SETTING_FIELD)"
  />
</template>
