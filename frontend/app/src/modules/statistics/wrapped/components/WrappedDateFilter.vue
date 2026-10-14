<script setup lang="ts">
import dayjs from 'dayjs';
import DateTimeRangePicker from '@/modules/shell/components/inputs/DateTimeRangePicker.vue';

/**
 * The analysed period: quick picks for all time and the last two calendar years, and the exact
 * dates. A change applies on its own; the page fetches once the range settles. The controls stay
 * usable during a fetch, since a change made then runs once that fetch ends.
 */
const start = defineModel<number | undefined>('start', {
  get(value: number | undefined) {
    return value || undefined;
  },
  required: true,
  set(value: number | undefined) {
    return value || 0;
  },
});

const end = defineModel<number>('end', { required: true });

const { t } = useI18n({ useScope: 'global' });

const ALL_TIME = 'all';

const invalidRange = computed<boolean>(() => {
  const from = get(start);
  const to = get(end);
  return !!from && !!to && from > to;
});

const currentYear = dayjs().year();
const years = [currentYear, currentYear - 1];

function yearRange(year: number): { start: number; end: number } {
  return {
    end: Math.min(dayjs().year(year).endOf('year').unix(), dayjs().unix()),
    start: dayjs().year(year).startOf('year').unix(),
  };
}

/** The pick the range matches, if any; exact dates of another span select none. */
const preset = computed<string | number | undefined>({
  get() {
    if (!get(start))
      return ALL_TIME;
    return years.find((year) => {
      const range = yearRange(year);
      return get(start) === range.start && (get(end) === range.end || year === currentYear);
    });
  },
  set(value: string | number | undefined) {
    if (value === undefined)
      return;
    if (value === ALL_TIME) {
      set(start, undefined);
      set(end, dayjs().unix());
      return;
    }
    const range = yearRange(Number(value));
    set(start, range.start);
    set(end, range.end);
  },
});
</script>

<template>
  <div
    class="flex flex-col lg:flex-row gap-x-4 gap-y-3 lg:items-start"
    :class="{ '-mb-6': !invalidRange }"
  >
    <RuiButtonGroup
      v-model="preset"
      variant="segmented"
      size="sm"
      class="self-start lg:mt-6 [&>button]:h-7"
      data-testid="wrapped-presets"
    >
      <RuiButton :model-value="ALL_TIME">
        {{ t('wrapped.all_time') }}
      </RuiButton>
      <RuiButton
        v-for="year in years"
        :key="year"
        :model-value="year"
      >
        {{ year }}
      </RuiButton>
    </RuiButtonGroup>
    <DateTimeRangePicker
      v-model:start="start"
      v-model:end="end"
      class="flex-1 max-w-3xl"
      dense
      allow-empty
      max-end-date="now"
    />
  </div>
</template>
