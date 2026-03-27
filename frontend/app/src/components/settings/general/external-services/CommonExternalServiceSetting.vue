<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { useMonitorService } from '@/modules/app/use-monitor-service';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { toMessages } from '@/utils/validation';

const {
  defaultValue,
  hint = '',
  label = '',
  min = 1,
  minValueMessage,
  requiredMessage,
  setting,
} = defineProps<{
  setting: 'queryRetryLimit' | 'connectTimeout' | 'readTimeout';
  min?: number;
  requiredMessage: string;
  minValueMessage: (min: number) => string;
  label?: string;
  hint?: string;
  defaultValue: number;
}>();

const inputValue = ref<string>('');

const rules = {
  inputValue: {
    min: helpers.withMessage(minValueMessage(min), minValue(min)),
    required: helpers.withMessage(requiredMessage, required),
  },
};

const { [setting]: storeValue } = storeToRefs(useGeneralSettingsStore());

function resetValue() {
  set(inputValue, get(storeValue).toString());
}

const v$ = useVuelidate(rules, { inputValue }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { restart } = useMonitorService();

function transform(value: string) {
  return value ? Number.parseInt(value) : value;
}

function reset(update: (value: number) => void) {
  update(defaultValue);
  set(inputValue, defaultValue.toString());
}

onMounted(() => {
  resetValue();
});
</script>

<template>
  <div>
    <SettingsOption
      class="mt-1"
      :setting="setting"
      :transform="transform"
      @updated="restart()"
      @finished="resetValue()"
    >
      <template #title>
        {{ label }}
      </template>
      <template #subtitle>
        {{ hint }}
      </template>
      <template #default="{ error, success, update, updateImmediate }">
        <div class="flex items-start w-full">
          <RuiTextField
            v-model="inputValue"
            variant="outlined"
            color="primary"
            type="number"
            class="w-full"
            :min="min"
            :success-messages="success"
            :error-messages="error || toMessages(v$.inputValue)"
            @update:model-value="callIfValid($event, update)"
          />
          <SettingResetConfirmButton @confirm="reset(updateImmediate)" />
        </div>
      </template>
    </SettingsOption>
  </div>
</template>
