<script setup lang="ts">
import type { PeriodChangedEvent, SelectionChangedEvent } from '@/types/reports';
import type { Quarter } from '@/types/settings/frontend-settings';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import DateTimeRangePicker from '@/components/inputs/DateTimeRangePicker.vue';
import ReportPeriodSelector from '@/components/profitloss/ReportPeriodSelector.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<{ start: number; end: number }>({ required: true });

const emit = defineEmits<{
  (e: 'update:valid', valid: boolean): void;
}>();

const store = useFrontendSettingsStore();
const { profitLossReportPeriod } = storeToRefs(store);

const year = computed<string>(() => get(profitLossReportPeriod).year);
const quarter = computed<Quarter>(() => get(profitLossReportPeriod).quarter);
const custom = computed<boolean>(() => get(year) === 'custom');

const start = useRefPropVModel(modelValue, 'start');
const end = useRefPropVModel(modelValue, 'end');

function input(data: { start: number; end: number }): void {
  set(modelValue, data);
}

function updateValid(valid: boolean): void {
  emit('update:valid', valid);
}

async function onChanged(event: SelectionChangedEvent): Promise<void> {
  if (event.year === 'custom')
    input({ end: dayjs().unix(), start: 0 });

  await store.updateSetting({
    profitLossReportPeriod: event,
  });
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
