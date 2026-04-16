<script setup lang="ts">
import type { Dayjs } from 'dayjs';

const model = defineModel<Dayjs>({ required: true });

function prevMonth() {
  const prevMonth = get(model).subtract(1, 'month');
  set(model, prevMonth);
}

function nextMonth() {
  const nextMonth = get(model).add(1, 'month');
  set(model, nextMonth);
}

const readableMonthAndYear = computed(() => get(model).format('MMMM YYYY'));
</script>

<template>
  <div class="flex">
    <RuiButton
      variant="text"
      icon
      class="!p-2"
      @click="prevMonth()"
    >
      <RuiIcon name="lu-chevron-left" />
    </RuiButton>
    <RuiButton
      variant="text"
      icon
      class="!p-2"
      @click="nextMonth()"
    >
      <RuiIcon name="lu-chevron-right" />
    </RuiButton>
    <div class="pl-4">
      <RuiTextField
        class="cursor-pointer"
        :model-value="readableMonthAndYear"
        variant="outlined"
        color="primary"
        readonly
        dense
        hide-details
        append-icon="lu-calendar-days"
      />
    </div>
  </div>
</template>
