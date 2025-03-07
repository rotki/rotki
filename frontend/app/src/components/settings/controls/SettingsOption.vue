<script setup lang="ts">
import type { SessionSettings } from '@/types/session';
import type { FrontendSettingsPayload } from '@/types/settings/frontend-settings';
import type { SettingsUpdate } from '@/types/user';
import type { MaybeRef } from '@vueuse/core';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import { SettingLocation, useClearableMessages, useSettings } from '@/composables/settings';

type TransformMessageCallback<T = any> = (value: any) => T;

const props = withDefaults(
  defineProps<{
    setting: keyof SettingsUpdate | keyof FrontendSettingsPayload | keyof SessionSettings;
    frontendSetting?: boolean;
    sessionSetting?: boolean;
    transform?: TransformMessageCallback | null;
    successMessage?: string | TransformMessageCallback<string>;
    errorMessage?: string | TransformMessageCallback<string>;
  }>(),
  {
    errorMessage: '',
    frontendSetting: false,
    sessionSetting: false,
    successMessage: '',
    transform: null,
  },
);

const emit = defineEmits(['updated', 'finished']);

const { errorMessage, frontendSetting, sessionSetting, setting, successMessage, transform } = toRefs(props);
const { clearAll, error, setError, setSuccess, stop, success, wait } = useClearableMessages();
const { updateSetting } = useSettings();

const loading = ref(false);

function getMessage(messageRef: MaybeRef<string | TransformMessageCallback<string>>, value: any) {
  const message = get(messageRef);
  if (typeof message === 'string')
    return message;

  return message(value);
}

async function updateImmediate(newValue: any) {
  stop();
  clearAll();
  set(loading, true);
  const func = get(transform);
  const settingKey = get(setting);
  const settingValue = func ? func(newValue) : newValue;

  const location = get(sessionSetting)
    ? SettingLocation.SESSION
    : get(frontendSetting)
      ? SettingLocation.FRONTEND
      : SettingLocation.GENERAL;

  const result = await updateSetting(settingKey, settingValue, location, {
    error: getMessage(errorMessage, newValue),
    success: getMessage(successMessage, newValue),
  });

  set(loading, false);
  await wait();

  if ('success' in result) {
    emit('updated');
    setSuccess(result.success, true);
  }
  else {
    setError(result.error, true);
  }
  emit('finished');
}

const debounceUpdate = useDebounceFn(updateImmediate, 1500);

function update(newValue: any) {
  clearAll();
  debounceUpdate(newValue);
}
</script>

<template>
  <SettingsItem>
    <template
      v-if="$slots.title"
      #title
    >
      <slot name="title" />
    </template>
    <template
      v-if="$slots.subtitle"
      #subtitle
    >
      <slot name="subtitle" />
    </template>
    <slot
      :error="error"
      :success="success"
      :update="update"
      :update-immediate="updateImmediate"
      :loading="loading"
    />
  </SettingsItem>
</template>
