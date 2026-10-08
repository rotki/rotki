<script setup lang="ts">
import dayjs from 'dayjs';
import {
  AsOfPreset,
  asOfTimestamp,
  type DateKey,
  presetDateKey,
  toDateKey,
} from '@/modules/statistics/historical-balances/as-of-date';

interface PresetOption {
  preset: AsOfPreset;
  day: DateKey;
  label: string;
}

const day = defineModel<DateKey>({ required: true });

const { t } = useI18n({ useScope: 'global' });

/**
 * The picker works in unix seconds and shows the as-of time the day stands for, so it never reads
 * as the day's start. The page only keeps the day, so any time picked is dropped.
 */
const pickerValue = computed<number>({
  get: () => asOfTimestamp(get(day), dayjs().unix()),
  set: (value: number) => {
    set(day, toDateKey(value));
  },
});

const presets = computed<PresetOption[]>(() => {
  const now = dayjs().unix();
  const yearEnd = (preset: AsOfPreset): { day: DateKey; year: number } => {
    const presetDay = presetDateKey(preset, now);
    return { day: presetDay, year: dayjs(presetDay).year() };
  };
  const lastYear = yearEnd(AsOfPreset.END_OF_LAST_YEAR);
  const yearBefore = yearEnd(AsOfPreset.END_OF_YEAR_BEFORE);
  return [
    { day: presetDateKey(AsOfPreset.TODAY, now), label: t('historical_balances.as_of.today'), preset: AsOfPreset.TODAY },
    { day: lastYear.day, label: t('historical_balances.as_of.end_of_year', { year: lastYear.year }), preset: AsOfPreset.END_OF_LAST_YEAR },
    { day: yearBefore.day, label: t('historical_balances.as_of.end_of_year', { year: yearBefore.year }), preset: AsOfPreset.END_OF_YEAR_BEFORE },
  ];
});
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <RuiDateTimePicker
      v-model="pickerValue"
      class="w-56"
      type="epoch"
      max-date="now"
      partial-time="end"
      :label="t('historical_balances.as_of.label')"
      variant="outlined"
      dense
      hide-details
      data-testid="historical-balances-as-of-picker"
    />
    <div class="flex flex-wrap gap-2">
      <RuiButton
        v-for="option in presets"
        :key="option.preset"
        size="sm"
        :variant="day === option.day ? 'default' : 'outlined'"
        :color="day === option.day ? 'primary' : undefined"
        :data-testid="`historical-balances-preset-${option.preset}`"
        @click="day = option.day"
      >
        {{ option.label }}
      </RuiButton>
    </div>
  </div>
</template>
