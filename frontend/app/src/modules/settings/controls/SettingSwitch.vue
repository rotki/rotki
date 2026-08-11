<script setup lang="ts">
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Generic owning component for a boolean setting. Given a registry key it manages its own local draft
 * and persistence through `useSettingModel` (the writer pipeline), and surfaces the same "Settings
 * saved" / error messages the hand-written toggles did. Place it inside a `SettingsItem` for the
 * title/subtitle; this renders only the switch (or checkbox).
 *
 * `inverted` flips the displayed state against the stored value (e.g. an "animations note" toggle that
 * shows the opposite of `animationsEnabled`). Extra attributes (data-testid, size, class, hint) are
 * forwarded to the underlying control.
 */
defineOptions({ inheritAttrs: false });

const {
  setting,
  label = '',
  inverted = false,
  control = 'switch',
  successMessage = '',
  errorMessage = '',
  debounce = 0,
} = defineProps<{
  setting: WritableSettingKeyOf<boolean | null | undefined>;
  label?: string;
  /** Show and write the negation of the stored value. */
  inverted?: boolean;
  control?: 'switch' | 'checkbox';
  /** Static text, or a callback given the displayed value (e.g. distinct enabled/disabled copy). */
  successMessage?: string | ((value: boolean) => string);
  errorMessage?: string;
  debounce?: number;
}>();

const emit = defineEmits<{
  /** Fired after a successful persist, mirroring the old `SettingsOption` `@finished` hook. */
  updated: [value: boolean];
}>();

const { error: writeError, model, success: writeSuccess } = useSettingModel(setting, { debounce });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

// The control needs a plain boolean; nullable-boolean settings read `null`/`undefined` before the user
// has ever toggled them, which we treat as off. `inverted` flips both the read and the written value.
const enabled = computed<boolean>({
  get: () => {
    const value = get(model) ?? false;
    return inverted ? !value : value;
  },
  set: (value) => {
    set(model, inverted ? !value : value);
  },
});

watch(model, () => {
  clearAll();
});

watch(writeSuccess, (saved) => {
  if (saved) {
    setSuccess(typeof successMessage === 'function' ? successMessage(get(enabled)) : successMessage, true);
    emit('updated', get(enabled));
  }
});

watch(writeError, (message) => {
  if (message)
    setError(errorMessage ? `${errorMessage}: ${message}` : message, true);
});
</script>

<template>
  <RuiCheckbox
    v-if="control === 'checkbox'"
    v-bind="$attrs"
    v-model="enabled"
    color="primary"
    :label="label"
    :success-messages="success"
    :error-messages="error"
  />
  <RuiSwitch
    v-else
    v-bind="$attrs"
    v-model="enabled"
    color="primary"
    :label="label"
    :success-messages="success"
    :error-messages="error"
  />
</template>
