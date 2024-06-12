<script setup lang="ts">
import type { Dayjs } from 'dayjs';

const props = defineProps<{
  value: Dayjs;
}>();

const emit = defineEmits<{
  (e: 'input', date: Dayjs): void;
}>();

const vModel = useSimpleVModel(props, emit);

function prevMonth() {
  const prevMonth = get(vModel).subtract(1, 'month');
  set(vModel, prevMonth);
}

function nextMonth() {
  const nextMonth = get(vModel).add(1, 'month');
  set(vModel, nextMonth);
}

const readableMonthAndYear = computed(() => get(vModel).format('MMMM YYYY'));
</script>

<template>
  <div class="flex">
    <RuiButton
      variant="text"
      icon
      class="!p-2"
      @click="prevMonth()"
    >
      <RuiIcon name="arrow-left-s-line" />
    </RuiButton>
    <RuiButton
      variant="text"
      icon
      class="!p-2"
      @click="nextMonth()"
    >
      <RuiIcon name="arrow-right-s-line" />
    </RuiButton>
    <div class="pl-4">
      <RuiTextField
        class="cursor-pointer"
        :value="readableMonthAndYear"
        variant="outlined"
        color="primary"
        readonly
        dense
        hide-details
        append-icon="calendar-line"
      />
    </div>
  </div>
</template>
