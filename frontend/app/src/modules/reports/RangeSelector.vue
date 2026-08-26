<script setup lang="ts">
import type { PeriodChangedEvent, SelectionChangedEvent } from '@/modules/reports/report-types';
import type { Quarter } from '@/modules/settings/types/frontend-settings';
import dayjs from 'dayjs';
import { z, type ZodType } from 'zod';
import { useModelForm } from '@/modules/core/form/use-model-form';
import ReportPeriodSelector from '@/modules/reports/ReportPeriodSelector.vue';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import DateTimeRangePicker from '@/modules/shell/components/inputs/DateTimeRangePicker.vue';

interface ReportRange {
  start: number | undefined;
  end: number;
}

const modelValue = defineModel<ReportRange>({ required: true });

const emit = defineEmits<{
  'update:valid': [valid: boolean];
}>();

const { t } = useI18n({ useScope: 'global' });

const profitLossReportPeriod = useSetting('profitLossReportPeriod');
const { updateFrontendSetting } = useSettingsOperations();

const year = computed<string>(() => get(profitLossReportPeriod).year);
const quarter = computed<Quarter>(() => get(profitLossReportPeriod).quarter);
const custom = computed<boolean>(() => get(year) === 'custom');

/**
 * Both dates are only required while the period is custom, which is a persisted setting rather than
 * part of the state, so the schema is rebuilt when it changes.
 *
 * They are numbers, so the rule catches a cleared picker and nothing else: the epoch is a date like
 * any other, which is what vuelidate's `required` reported too.
 */
const schema = computed<ZodType>(() => {
  if (!get(custom))
    return z.object({ end: z.number().optional(), start: z.number().optional() });

  return z.object({
    end: z.number({ error: t('generate.validation.empty_end_date') }),
    start: z.number({ error: t('generate.validation.empty_start_date') }),
  });
});

const form = useModelForm<ReportRange>({
  model: modelValue,
  schema,
});

function input(data: ReportRange): void {
  set(modelValue, data);
}

async function onChanged(event: SelectionChangedEvent): Promise<void> {
  if (event.year === 'custom') {
    input({ end: dayjs().unix(), start: undefined });
  }

  await updateFrontendSetting({
    profitLossReportPeriod: event,
  });
}

function onPeriodChange(period: PeriodChangedEvent | null): void {
  const now = dayjs().unix();
  if (period === null) {
    input({ end: now, start: undefined });
    return;
  }

  input({ end: Math.min(period.end, now), start: period.start });
}

// The validity is the only thing anything consumes: no field ever renders a message, because
// nothing touches them, which reproduces vuelidate's $autoDirty: false exactly.
watchImmediate(form.valid, (valid) => {
  emit('update:valid', valid);
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
      v-model:start="form.state.start"
      v-model:end="form.state.end"
      class="mt-1.5"
      allow-empty
      max-end-date="now"
      :start-error-messages="form.errors('start')"
      :end-error-messages="form.errors('end')"
    />
  </div>
</template>
