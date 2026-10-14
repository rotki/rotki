<script setup lang="ts">
import type { Dayjs } from 'dayjs';

const model = defineModel<Dayjs>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const readableMonthAndYear = computed<string>(() => get(model).format('MMMM YYYY'));

function prevMonth(): void {
  set(model, get(model).subtract(1, 'month'));
}

function nextMonth(): void {
  set(model, get(model).add(1, 'month'));
}
</script>

<template>
  <div class="flex items-center gap-1">
    <RuiButton
      variant="text"
      icon
      size="sm"
      :aria-label="t('calendar.previous_month')"
      data-testid="calendar-prev-month"
      @click="prevMonth()"
    >
      <RuiIcon name="lu-chevron-left" />
    </RuiButton>
    <RuiButton
      variant="text"
      icon
      size="sm"
      :aria-label="t('calendar.next_month')"
      data-testid="calendar-next-month"
      @click="nextMonth()"
    >
      <RuiIcon name="lu-chevron-right" />
    </RuiButton>
    <h2
      class="m-0 ml-2 min-w-36 text-lg font-medium text-rui-text"
      aria-live="polite"
      data-testid="calendar-month-label"
    >
      {{ readableMonthAndYear }}
    </h2>
  </div>
</template>
