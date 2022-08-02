<template>
  <div>
    <slot :error="error" :success="success" :update="update" />
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType, toRefs, watch } from '@vue/composition-api';
import { get, MaybeRef } from '@vueuse/core';
import { getSessionState } from '@/composables/session';
import {
  SettingLocation,
  useClearableMessages,
  useSettings
} from '@/composables/settings';
import { EditableSessionState } from '@/store/session/types';
import { FrontendSettingsPayload } from '@/types/frontend-settings';
import { SettingsUpdate } from '@/types/user';
import { logger } from '@/utils/logging';

export default defineComponent({
  name: 'SettingsOption',
  props: {
    setting: {
      required: true,
      type: String as PropType<
        | keyof SettingsUpdate
        | keyof FrontendSettingsPayload
        | keyof EditableSessionState
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
  },
  emits: ['updated', 'finished'],
  setup(props, { emit }) {
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
    const {
      frontendSettings,
      generalSettings,
      accountingSettings,
      updateSetting
    } = useSettings();

    const sessionState = getSessionState();

    watch(
      [setting, frontendSetting, sessionSetting],
      ([setting, frontend, session]) => {
        if (
          (session &&
            !Object.keys(get(sessionState)).includes(setting as string)) ||
          (frontend &&
            !Object.keys(get(frontendSettings)).includes(setting as string)) ||
          (!session &&
            !frontend &&
            !Object.keys(get(generalSettings)).includes(setting as string) &&
            !Object.keys(get(accountingSettings)).includes(setting as string))
        ) {
          logger.error(`Invalid setting options for setting: ${setting}`);
        }
      },
      { immediate: true }
    );

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

      let result = await updateSetting(settingKey, settingValue, location, {
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

    return {
      error,
      success,
      update
    };
  }
});
</script>
