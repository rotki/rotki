<script setup lang="ts">
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { DateFormat } from '@/types/date-format';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import dayjs, { type Dayjs } from 'dayjs';

const model = defineModel<Dayjs>({ required: true });

defineProps<{
  visibleDate: Dayjs;
  today: Dayjs;
}>();

const emit = defineEmits<{
  (e: 'set-today'): void;
}>();

const { t } = useI18n();

const datePicker = ref();
const datetime = ref<string>('0');

watch(
  model,
  (model) => {
    set(datetime, convertFromTimestamp(get(model).unix()));
  },
  {
    immediate: true,
  },
);

function goToSelectedDate() {
  const timestamp = convertToTimestamp(get(datetime), DateFormat.DateMonthYearHourMinuteSecond, true);

  set(model, dayjs(timestamp));
}
</script>

<template>
  <RuiButtonGroup
    color="primary"
    variant="outlined"
  >
    <RuiButton
      :disabled="visibleDate.isSame(today, 'day')"
      @click="emit('set-today')"
    >
      {{ t('calendar.today') }}
    </RuiButton>
    <RuiMenu wrapper-class="h-full">
      <template #activator="{ attrs }">
        <RuiButton
          size="sm"
          class="!p-2 !outline-none h-full"
          color="primary"
          variant="outlined"
          v-bind="attrs"
        >
          <RuiIcon
            size="20"
            name="lu-chevron-down"
          />
        </RuiButton>
      </template>
      <div class="p-4 flex items-start">
        <DateTimePicker
          ref="datePicker"
          v-model="datetime"
          class="w-[12rem] [&_fieldset]:!rounded-r-none"
          dense
          :label="t('calendar.go_to_date')"
          date-only
          input-only
          @keydown.enter="goToSelectedDate()"
        />
        <RuiButton
          color="primary"
          :disabled="!datePicker?.valid"
          class="!rounded-l-none !p-2 !py-2.5"
          @click="goToSelectedDate()"
        >
          <RuiIcon
            name="lu-corner-down-left"
            size="20"
          />
        </RuiButton>
      </div>
    </RuiMenu>
  </RuiButtonGroup>
</template>
