<script setup lang="ts">
import type { MaybeRef } from 'vue';
import type { SessionSettings } from '@/modules/session/types';
import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import type { SettingsUpdate } from '@/modules/settings/types/user-settings';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { SettingLocation, useSettings } from '@/modules/settings/use-settings';

type TransformMessageCallback<T = any> = (value: any) => T;

const {
  errorMessage = '',
  frontendSetting = false,
  sessionSetting = false,
  setting,
  successMessage = '',
  transform = null,
} = defineProps<{
  setting: keyof SettingsUpdate | keyof FrontendSettingsPayload | keyof SessionSettings;
  frontendSetting?: boolean;
  sessionSetting?: boolean;
  transform?: TransformMessageCallback | null;
  successMessage?: string | TransformMessageCallback<string>;
  errorMessage?: string | TransformMessageCallback<string>;
}>();

const emit = defineEmits<{
  updated: [];
  finished: [];
}>();
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
  const settingValue = transform ? transform(newValue) : newValue;

  let location: SettingLocation;
  if (sessionSetting)
    location = SettingLocation.SESSION;
  else if (frontendSetting)
    location = SettingLocation.FRONTEND;
  else
    location = SettingLocation.GENERAL;

  const result = await updateSetting(setting, settingValue, location, {
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
