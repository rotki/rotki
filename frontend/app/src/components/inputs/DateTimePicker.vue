<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers } from '@vuelidate/validators';
import dayjs, { type Dayjs } from 'dayjs';
import { millisecondsToSeconds } from '@/utils/date';
import { toMessages } from '@/utils/validation';

interface DateTimePickerProps {
  limitNow?: boolean;
  milliseconds?: boolean;
  minValue?: number;
  maxValue?: number;
  errorMessages?: string[] | string;
}

const modelValue = defineModel<number>({ required: true });

const props = withDefaults(defineProps<DateTimePickerProps>(), {
  errorMessages: () => [],
  limitNow: false,
  milliseconds: false,
});

const { t } = useI18n({ useScope: 'global' });

const { errorMessages, limitNow, maxValue, milliseconds, minValue } = toRefs(props);

const now = ref<Dayjs>(dayjs());

function normalizeTimestamp(timestamp: number, multiply = false) {
  const ms = get(milliseconds);
  if (ms) {
    return timestamp;
  }
  if (multiply) {
    return timestamp * 1000;
  }
  return millisecondsToSeconds(timestamp);
}

const maxDate = computed(() => {
  const nowVal = get(now);
  const propMaxValue = get(maxValue);
  const max = propMaxValue ? normalizeTimestamp(propMaxValue, true) : Infinity;
  const nowValue = get(limitNow) && nowVal ? nowVal.valueOf() : Infinity;

  const compared = Math.min(max, nowValue);
  return compared === Infinity ? undefined : compared;
});

const minDate = computed(() => {
  const min = get(minValue);
  if (min) {
    return normalizeTimestamp(min, true);
  }
  return undefined;
});

function passLimitNowFilter(value: number) {
  const max = get(maxDate);
  if (!get(limitNow) || !max) {
    return true;
  }

  return value <= max;
}

const rules = {
  date: {
    isOnLimit: helpers.withMessage(t('date_time_picker.limit_now'), (v: number): boolean => passLimitNowFilter(v)),
  },
};

const v$ = useVuelidate(rules, {
  date: modelValue,
}, {
  $autoDirty: true,
  $externalResults: computed(() => ({ date: get(errorMessages) })),
  $stopPropagation: true,
});

watchImmediate([modelValue, limitNow], ([_, limitNow]) => {
  if (limitNow) {
    set(now, dayjs());
  }
});
</script>

<template>
  <RuiDateTimePicker
    v-model="modelValue"
    color="primary"
    variant="outlined"
    :type="milliseconds ? 'epoch-ms' : 'epoch'"
    :accuracy="milliseconds ? 'millisecond' : 'second'"
    :max-date="maxDate"
    :min-date="minDate"
    :error-messages="toMessages(v$.date)"
  />
</template>
