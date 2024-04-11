<script setup lang="ts">
import dayjs, { type Dayjs } from 'dayjs';
import { DateFormat } from '@/types/date-format';

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

const datetime = computed({
  get() {
    return convertFromTimestamp(get(vModel).unix());
  },
  set(value: string) {
    const timestamp = convertToTimestamp(
      value,
      DateFormat.DateMonthYearHourMinuteSecond,
      true,
    );

    set(vModel, dayjs(timestamp));
  },
});

const readableMonthAndYear = computed(() => get(vModel).format('MMMM YYYY'));

const { t } = useI18n();
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
      <RuiMenu>
        <template #activator="{ on }">
          <RuiTextField
            class="cursor-pointer"
            :value="readableMonthAndYear"
            variant="outlined"
            color="primary"
            readonly
            dense
            hide-details
            append-icon="calendar-line"
            v-on="on"
          />
        </template>
        <div class="p-4">
          <DateTimePicker
            v-model="datetime"
            :label="t('calendar.go_to_date')"
            date-only
            input-only
          />
        </div>
      </RuiMenu>
    </div>
  </div>
</template>
