<script setup lang="ts">
import type { PeriodChangedEvent, SelectionChangedEvent } from '@/modules/reports/report-types';
import type { Quarter } from '@/modules/settings/types/frontend-settings';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { useRefPropVModel } from '@/modules/core/common/validation/model';
import { toMessages } from '@/modules/core/common/validation/validation';
import ReportPeriodSelector from '@/modules/reports/ReportPeriodSelector.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import DateTimeRangePicker from '@/modules/shell/components/inputs/DateTimeRangePicker.vue';

const modelValue = defineModel<{ start: number | undefined; end: number }>({ required: true });

const emit = defineEmits<{
  'update:valid': [valid: boolean];
}>();

const store = useFrontendSettingsStore();
const { profitLossReportPeriod } = storeToRefs(store);
const { updateFrontendSetting } = useSettingsOperations();

const year = computed<string>(() => get(profitLossReportPeriod).year);
const quarter = computed<Quarter>(() => get(profitLossReportPeriod).quarter);
const custom = computed<boolean>(() => get(year) === 'custom');

const start = useRefPropVModel(modelValue, 'start');
const end = useRefPropVModel(modelValue, 'end');

function input(data: { start: number | undefined; end: number }): void {
  set(modelValue, data);
}

function updateValid(valid: boolean): void {
  emit('update:valid', valid);
}

async function onChanged(event: SelectionChangedEvent): Promise<void> {
  await updateFrontendSetting({
    profitLossReportPeriod: event,
  });

  if (event.year === 'custom') {
    await nextTick();
    input({ end: dayjs().unix(), start: undefined });
  }
}

function onPeriodChange(period: PeriodChangedEvent | null): void {
  const now = dayjs().unix();
  if (period === null) {
    input({ end: now, start: 0 });
    return;
  }

  const start = period.start;
  let end = period.end;
  end = Math.min(end, now);
  input({ end, start });
}

const { t } = useI18n({ useScope: 'global' });

const rules = {
  end: {
    required: helpers.withMessage(t('generate.validation.empty_end_date'), requiredIf(custom)),
  },
  start: {
    required: helpers.withMessage(t('generate.validation.empty_start_date'), requiredIf(custom)),
  },
};

const v$ = useVuelidate(
  rules,
  {
    end,
    start,
  },
  { $autoDirty: false },
);

watchImmediate(v$, ({ $invalid }) => {
  updateValid(!$invalid);
});
</script>

<template>
  <div class="range-selector flex flex-col gap-4">
    <ReportPeriodSelector
      :year="year"
      :quarter="quarter"
      @update:period="onPeriodChange($event)"
      @update:selection="onChanged($event)"
    />
    <DateTimeRangePicker
      v-if="custom"
      v-model:start="start"
      v-model:end="end"
      class="mt-1.5"
      allow-empty
      max-end-date="now"
      :start-error-messages="toMessages(v$.start)"
      :end-error-messages="toMessages(v$.end)"
    />
  </div>
</template>
