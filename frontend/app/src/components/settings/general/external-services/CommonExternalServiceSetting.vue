<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

const props = withDefaults(
  defineProps<{
    setting: 'queryRetryLimit' | 'connectTimeout' | 'readTimeout';
    min?: number;
    requiredMessage: string;
    minValueMessage: (min: number) => string;
    label?: string;
    hint?: string;
  }>(),
  {
    min: 1,
    label: '',
    hint: '',
  },
);

const { min, setting, requiredMessage, minValueMessage } = toRefs(props);

const inputValue = ref<string>('');

const rules = {
  inputValue: {
    required: helpers.withMessage(get(requiredMessage), required),
    min: helpers.withMessage(get(minValueMessage)(get(min)), minValue(get(min))),
  },
};

const { [get(setting)]: storeValue } = storeToRefs(useGeneralSettingsStore());

function resetValue() {
  set(inputValue, get(storeValue).toString());
}

const v$ = useVuelidate(rules, { inputValue }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { restart } = useMonitorStore();

const transform = (value: string) => (value ? Number.parseInt(value) : value);

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
      <template
        #default="{ error, success, update }"
      >
        <RuiTextField
          v-model="inputValue"
          variant="outlined"
          color="primary"
          type="number"
          :min="min"
          :success-messages="success"
          :error-messages="error || toMessages(v$.inputValue)"
          @update:model-value="callIfValid($event, update)"
        />
      </template>
    </SettingsOption>
  </div>
</template>
