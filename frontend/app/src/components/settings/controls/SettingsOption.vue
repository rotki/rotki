<script setup lang="ts">
import { type MaybeRef } from '@vueuse/core';
import { type PropType } from 'vue';
import { type SessionSettings } from '@/store/settings/session';
import { type FrontendSettingsPayload } from '@/types/frontend-settings';
import { type SettingsUpdate } from '@/types/user';

const props = defineProps({
  setting: {
    required: true,
    type: String as PropType<
      | keyof SettingsUpdate
      | keyof FrontendSettingsPayload
      | keyof SessionSettings
    >
  },
  frontendSetting: {
    required: false,
    type: Boolean,
    default: false
  },
  sessionSetting: {
    required: false,
    type: Boolean,
    default: false
  },
  transform: {
    required: false,
    type: Function as PropType<(value: any) => any>,
    default: null
  },
  successMessage: {
    required: false,
    type: [String, Function] as PropType<((value: any) => string) | string>,
    default: ''
  },
  errorMessage: {
    required: false,
    type: [String, Function] as PropType<((value: any) => string) | string>,
    default: ''
  }
});

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
  ref: MaybeRef<string | ((value: any) => string)>,
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
