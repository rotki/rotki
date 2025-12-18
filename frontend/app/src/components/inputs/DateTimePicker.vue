<script setup lang="ts">
import type { RuiDateTimePickerProps } from '@rotki/ui-library/components';
import dayjs, { type ManipulateType } from 'dayjs';

interface QuickOption {
  label: string;
  unit: ManipulateType;
  value: number;
}

const modelValue = defineModel<number>({ required: true });

const props = defineProps<RuiDateTimePickerProps>();

const { t } = useI18n({ useScope: 'global' });

const quickOptions: QuickOption[] = [
  { label: t('date_time_picker.one_day_before'), unit: 'day', value: 1 },
  { label: t('date_time_picker.week_before'), unit: 'week', value: 1 },
  { label: t('date_time_picker.month_before'), unit: 'month', value: 1 },
  { label: t('date_time_picker.days_before', { days: 90 }), unit: 'day', value: 90 },
  { label: t('date_time_picker.months_before', { months: 6 }), unit: 'month', value: 6 },
  { label: t('date_time_picker.year_before'), unit: 'year', value: 1 },
];

const useMilliseconds = computed<boolean>(() => props.accuracy === 'millisecond');

function applyQuickOption(option: QuickOption): void {
  const currentValue = get(modelValue);
  const currentDate = get(useMilliseconds) ? dayjs(currentValue) : dayjs.unix(currentValue);
  const date = currentDate.subtract(option.value, option.unit);
  set(modelValue, get(useMilliseconds) ? date.valueOf() : date.unix());
}
</script>

<template>
  <RuiDateTimePicker
    v-model="modelValue"
    v-bind="props"
  >
    <template #menu-content>
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
    </template>
  </RuiDateTimePicker>
</template>
