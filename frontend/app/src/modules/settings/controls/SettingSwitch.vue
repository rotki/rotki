<script setup lang="ts">
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Generic owning component for a boolean setting. Given a registry key it manages its own local draft
 * and persistence through `useSettingModel` (the writer pipeline), and surfaces the same "Settings
 * saved" / error messages the hand-written toggles did. Place it inside a `SettingsItem` for the
 * title/subtitle; this renders only the switch.
 */
const {
  setting,
  label = '',
  successMessage = '',
  errorMessage = '',
  debounce = 0,
} = defineProps<{
  setting: WritableSettingKeyOf<boolean>;
  label?: string;
  /** Static text, or a callback given the persisted value (e.g. distinct enabled/disabled copy). */
  successMessage?: string | ((value: boolean) => string);
  errorMessage?: string;
  debounce?: number;
}>();

const { error: writeError, model, success: writeSuccess } = useSettingModel(setting, { debounce });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

watch(model, () => {
  clearAll();
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess(typeof successMessage === 'function' ? successMessage(get(model)) : successMessage, true);
});

watch(writeError, (message) => {
  if (message)
    setError(errorMessage ? `${errorMessage}: ${message}` : message, true);
});
</script>

<template>
  <RuiSwitch
    v-model="model"
    color="primary"
    :label="label"
    :success-messages="success"
    :error-messages="error"
  />
</template>
