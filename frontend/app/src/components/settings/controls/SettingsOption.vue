<template>
  <div>
    <slot :error="error" :success="success" :update="update" />
  </div>
</template>

<script lang="ts">
import { get, MaybeRef } from '@vueuse/core';
import { defineComponent, PropType, toRefs } from 'vue';
import { useClearableMessages, useSettings } from '@/composables/settings';
import { SettingsUpdate } from '@/types/user';

export default defineComponent({
  name: 'SettingsOption',
  props: {
    setting: {
      required: true,
      type: String as PropType<keyof SettingsUpdate>
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
  emits: ['updated'],
  setup(props, { emit }) {
    const { setting, successMessage, errorMessage, transform } = toRefs(props);
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
      const result = await updateSetting(
        {
          [settingKey]: settingValue
        },
        {
          success: getMessage(successMessage, newValue),
          error: getMessage(errorMessage, newValue)
        }
      );

      await wait();

      if ('success' in result) {
        emit('updated', settingValue);
        setSuccess(result.success);
      } else {
        setError(result.error);
      }
    };

    return {
      error,
      success,
      update
    };
  }
});
</script>
