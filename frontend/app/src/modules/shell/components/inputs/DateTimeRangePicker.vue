<script setup lang="ts">
import { createReusableTemplate } from '@vueuse/core';
import dayjs, { type ManipulateType } from 'dayjs';

interface QuickOption {
  label: string;
  unit: ManipulateType;
  value: number;
}

const start = defineModel<number | undefined>('start', { required: true });
const end = defineModel<number | undefined>('end', { required: true });

const { allowEmpty = false, dense = false, disabled = false, endErrorMessages = [], endLabel = '', maxEndDate, startErrorMessages = [], startLabel = '' } = defineProps<{
  allowEmpty?: boolean;
  dense?: boolean;
  disabled?: boolean;
  endErrorMessages?: string[];
  endLabel?: string;
  maxEndDate?: number | 'now';
  startErrorMessages?: string[];
  startLabel?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const [DefineQuickOptions, ReuseQuickOptions] = createReusableTemplate();

const quickOptions: QuickOption[] = [
  { label: t('date_time_range_picker.last_12_hours'), unit: 'hour', value: 12 },
  { label: t('date_time_range_picker.last_24_hours'), unit: 'hour', value: 24 },
  { label: t('date_time_range_picker.last_7_days'), unit: 'day', value: 7 },
  { label: t('date_time_range_picker.last_1_month'), unit: 'month', value: 1 },
  { label: t('date_time_range_picker.last_90_days'), unit: 'day', value: 90 },
  { label: t('date_time_range_picker.last_6_months'), unit: 'day', value: 180 },
  { label: t('date_time_range_picker.last_1_year'), unit: 'year', value: 1 },
];

const startLabelComputed = computed<string>(() => startLabel || t('generate.labels.start_date'));
const endLabelComputed = computed<string>(() => endLabel || t('generate.labels.end_date'));

const invalidRange = computed<boolean>(() => {
  const startVal = get(start);
  const endVal = get(end);
  return isDefined(startVal) && isDefined(endVal) && startVal > endVal;
});

const startErrorMessagesComputed = computed<string[]>(() => {
  if (get(invalidRange)) {
    return [t('generate.validation.end_after_start')];
  }
  return startErrorMessages;
});

const endErrorMessagesComputed = computed<string[]>(() => {
  if (get(invalidRange)) {
    return [' '];
  }
  return endErrorMessages;
});

function applyQuickOption(option: QuickOption): void {
  // Update `end` before `start` so the start picker's max-date constraint
  // (bound to `end`) widens before the new start is written. Otherwise a
  // transient state where start > end can latch a validation error in the
  // start picker that won't clear until the user changes modelValue again —
  // see RuiDateTimePicker's isDateValid, which only re-runs on modelValue
  // changes, not on min/max-date prop changes.
  const now = dayjs();
  set(end, now.unix());
  nextTick(() => {
    set(start, now.subtract(option.value, option.unit).unix());
  });
}
</script>

<template>
  <div class="grid md:grid-cols-2 gap-4">
    <DefineQuickOptions>
      <div class="border-t border-default flex flex-col pt-2">
        <RuiButton
          v-for="option in quickOptions"
          :key="`${option.value}-${option.unit}`"
          variant="list"
          size="sm"
          @click="applyQuickOption(option)"
        >
          {{ option.label }}
        </RuiButton>
      </div>
    </DefineQuickOptions>
    <RuiDateTimePicker
      v-model="start"
      :label="startLabelComputed"
      :max-date="end || undefined"
      :disabled="disabled"
      :dense="dense"
      :allow-empty="allowEmpty"
      type="epoch"
      variant="outlined"
      :error-messages="startErrorMessagesComputed"
    >
      <template #menu-content>
        <ReuseQuickOptions />
      </template>
    </RuiDateTimePicker>
    <RuiDateTimePicker
      v-model="end"
      :label="endLabelComputed"
      :min-date="start || undefined"
      :max-date="maxEndDate"
      :disabled="disabled"
      :dense="dense"
      :allow-empty="allowEmpty"
      type="epoch"
      variant="outlined"
      :error-messages="endErrorMessagesComputed"
    >
      <template #menu-content>
        <ReuseQuickOptions />
      </template>
    </RuiDateTimePicker>
  </div>
</template>
