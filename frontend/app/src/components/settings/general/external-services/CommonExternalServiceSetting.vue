<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { useMonitorStore } from '@/store/monitor';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';

const props = withDefaults(defineProps<{
  setting: 'queryRetryLimit' | 'connectTimeout' | 'readTimeout';
  min?: number;
  requiredMessage: string;
  minValueMessage: (min: number) => string;
  label?: string;
  hint?: string;
  defaultValue: number;
}>(), {
  hint: '',
  label: '',
  min: 1,
});

const { min, minValueMessage, requiredMessage, setting } = toRefs(props);

const inputValue = ref<string>('');

const rules = {
  inputValue: {
    min: helpers.withMessage(get(minValueMessage)(get(min)), minValue(get(min))),
    required: helpers.withMessage(get(requiredMessage), required),
  },
};

const { [get(setting)]: storeValue } = storeToRefs(useGeneralSettingsStore());

function resetValue() {
  set(inputValue, get(storeValue).toString());
}

const v$ = useVuelidate(rules, { inputValue }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { restart } = useMonitorStore();

function transform(value: string) {
  return value ? Number.parseInt(value) : value;
}

function reset(update: (value: number) => void) {
  update(props.defaultValue);
  set(inputValue, props.defaultValue.toString());
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
          <RuiButton
            class="mt-1 ml-2"
            variant="text"
            icon
            @click="reset(updateImmediate)"
          >
            <RuiIcon name="lu-history" />
          </RuiButton>
        </div>
      </template>
    </SettingsOption>
  </div>
</template>
