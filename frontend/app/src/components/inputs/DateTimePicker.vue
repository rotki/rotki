<script setup lang="ts">
import dayjs, { type ManipulateType } from 'dayjs';
import { omit } from 'es-toolkit/compat';

interface QuickOption {
  label: string;
  unit: ManipulateType;
  value: number;
}

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<number>({ required: true });

const attrs = useAttrs();
const filteredAttrs = computed(() => omit(attrs, ['modelValue', 'onUpdate:modelValue']));

const { t } = useI18n({ useScope: 'global' });

const quickOptions: QuickOption[] = [
  { label: t('date_time_picker.yesterday'), unit: 'day', value: 1 },
  { label: t('date_time_picker.week_before'), unit: 'week', value: 1 },
  { label: t('date_time_picker.month_before'), unit: 'month', value: 1 },
  { label: t('date_time_picker.days_before', { days: 90 }), unit: 'day', value: 90 },
  { label: t('date_time_picker.months_before', { months: 6 }), unit: 'month', value: 6 },
  { label: t('date_time_picker.year_before'), unit: 'year', value: 1 },
];

const useMilliseconds = computed<boolean>(() => attrs.accuracy === 'millisecond');

function applyQuickOption(option: QuickOption): void {
  const date = dayjs().subtract(option.value, option.unit);
  set(modelValue, get(useMilliseconds) ? date.valueOf() : date.unix());
}
</script>

<template>
  <RuiDateTimePicker
    v-model="modelValue"
    v-bind="filteredAttrs"
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
