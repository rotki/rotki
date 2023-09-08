<script setup lang="ts">
import { type MaybeRef } from '@vueuse/core';
import { type FrontendSettingsPayload } from '@/types/frontend-settings';
import { type SettingsUpdate } from '@/types/user';
import { type SessionSettings } from '@/types/session';

type TransformMessageCallback<T = any> = (value: any) => T;

const props = withDefaults(
  defineProps<{
    setting:
      | keyof SettingsUpdate
      | keyof FrontendSettingsPayload
      | keyof SessionSettings;
    frontendSetting?: boolean;
    sessionSetting?: boolean;
    transform?: TransformMessageCallback | null;
    successMessage?: string | TransformMessageCallback<string>;
    errorMessage?: string | TransformMessageCallback<string>;
  }>(),
  {
    frontendSetting: false,
    sessionSetting: false,
    transform: null,
    successMessage: '',
    errorMessage: ''
  }
);

const emit = defineEmits(['updated', 'finished']);

const {
  setting,
  frontendSetting,
  sessionSetting,
  successMessage,
  errorMessage,
  transform
} = toRefs(props);
const { error, success, clear, wait, stop, setSuccess, setError } =
  useClearableMessages();
const { updateSetting } = useSettings();

const getMessage = (
  ref: MaybeRef<string | TransformMessageCallback<string>>,
  value: any
) => {
  const message = get(ref);
  if (typeof message === 'string') {
    return message;
  }
  return message(value);
};

const update = async (newValue: any) => {
  stop();
  clear();
  const func = get(transform);
  const settingKey = get(setting);
  const settingValue = func ? func(newValue) : newValue;

  const location = get(sessionSetting)
    ? SettingLocation.SESSION
    : get(frontendSetting)
    ? SettingLocation.FRONTEND
    : SettingLocation.GENERAL;

  const result = await updateSetting(settingKey, settingValue, location, {
    success: getMessage(successMessage, newValue),
    error: getMessage(errorMessage, newValue)
  });

  await wait();

  if ('success' in result) {
    emit('updated');
    setSuccess(result.success);
  } else {
    setError(result.error);
  }
  emit('finished');
};
</script>

<template>
  <div>
    <slot :error="error" :success="success" :update="update" />
  </div>
</template>
