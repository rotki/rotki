<template>
  <div>
    <v-menu
      ref="menu"
      v-model="showMenu"
      :close-on-content-click="false"
      transition="scale-transition"
      offset-y
      max-width="580px"
      class="date-time-picker"
    >
      <template #activator="{ on }">
        <v-text-field
          ref="inputField"
          :value="inputtedDate"
          :label="label"
          :hint="hint"
          :disabled="disabled"
          prepend-inner-icon="mdi-calendar"
          :persistent-hint="persistentHint"
          :rules="allRules"
          :outlined="outlined"
          append-icon="mdi-clock-outline"
          :error-messages="errorMessages"
          @change="emitIfValid($event)"
          @click:append="setNow()"
          v-on="on"
        />
      </template>

      <div :class="$style.menu">
        <div>
          <v-date-picker
            elevation="0"
            class="rounded-0"
            :value="dateModel"
            :max="maxDate"
            @change="onDateChange($event)"
          />
          <v-time-picker
            elevation="0"
            class="rounded-0"
            :value="timeModel"
            :max="maxTime"
            format="24hr"
            :use-seconds="seconds"
            @change="onTimeChange($event)"
          />
        </div>
        <v-autocomplete
          v-model="selectedTimezone"
          class="pa-4 pb-0"
          outlined
          persistent-hint
          menu-pros="auto"
          :items="timezones"
          :rules="timezoneRule"
        />
      </div>
    </v-menu>
  </div>
</template>

<script setup lang="ts">
import dayjs from 'dayjs';
import { PropType, Ref } from 'vue';
import { timezones } from '@/data/timezones';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { DateFormat } from '@/types/date-format';
import {
  changeDateFormat,
  convertDateByTimezone,
  getDateInputISOFormat,
  isValidDate
} from '@/utils/date';

const defaultDateFormat = 'YYYY-MM-DD';

const isValid = (
  date: string,
  format: DateFormat,
  seconds: boolean = false
): boolean => {
  let dateFormat = getDateInputISOFormat(format);

  if (seconds) {
    return (
      isValidDate(date, dateFormat) ||
      isValidDate(date, `${dateFormat} HH:mm:ss`)
    );
  }
  return (
    isValidDate(date, dateFormat) || isValidDate(date, `${dateFormat} HH:mm`)
  );
};

const useRules = (
  rules: Ref<ValidationRules>,
  dateInputFormat: Ref<DateFormat>,
  seconds: Ref<boolean>,
  allowEmpty: Ref<boolean>
) => {
  const { t } = useI18n();
  const dateFormatRule = (date: string) => {
    const format = get(dateInputFormat);
    const dateFormat = getDateInputISOFormat(format);

    if (get(allowEmpty) && !date) {
      return true;
    }

    if (get(seconds)) {
      return (
        isValid(date, format, true) ||
        t('date_time_picker.seconds_format', {
          dateFormat
        }).toString()
      );
    }
    return (
      isValid(date, format) ||
      t('date_time_picker.default_format', {
        dateFormat
      }).toString()
    );
  };

  const allRules = computed(() => get(rules).concat(dateFormatRule));
  const timezoneRule = computed(() => [
    (v: string) =>
      !!v || t('date_time_picker.timezone_field.non_empty').toString()
  ]);

  return { allRules, timezoneRule };
};

type ValidationRules = ((v: string) => boolean | string)[];

const props = defineProps({
  label: { required: true, type: String },
  hint: { required: false, default: '', type: String },
  persistentHint: { required: false, default: false, type: Boolean },
  value: { default: '', required: false, type: String },
  rules: {
    default: () => [],
    required: false,
    type: Array as PropType<ValidationRules>
  },
  limitNow: { required: false, default: false, type: Boolean },
  allowEmpty: { required: false, default: false, type: Boolean },
  seconds: { required: false, default: false, type: Boolean },
  outlined: { required: false, default: false, type: Boolean },
  disabled: { required: false, default: false, type: Boolean },
  errorMessages: {
    required: false,
    default: () => [],
    type: Array as PropType<string[]>
  }
});

const emit = defineEmits<{ (e: 'input', value: string): void }>();

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const { seconds, rules, limitNow, value, allowEmpty } = toRefs(props);
const { allRules, timezoneRule } = useRules(
  rules,
  dateInputFormat,
  seconds,
  allowEmpty
);

const timeFormat = computed(() => {
  let format = 'HH:mm';
  if (get(seconds)) {
    format += ':ss';
  }
  return format;
});
const showMenu = ref(false);
const inputtedDate = ref('');
const selectedTimezone = ref('');
const timeModel = ref(dayjs().format(get(timeFormat)));
const dateModel = ref('');
const inputField = ref();

const maxDate = computed(() => {
  if (get(limitNow)) {
    return dayjs().format(defaultDateFormat);
  }
  return '';
});

const maxTime = computed(() => {
  if (get(limitNow) && dayjs(get(dateModel)).isToday()) {
    return dayjs().format(get(timeFormat));
  }
  return '';
});

function onValueChange(value: string) {
  const changedDateTimezone = convertDateByTimezone(
    value,
    DateFormat.DateMonthYearHourMinuteSecond,
    dayjs.tz.guess(),
    get(selectedTimezone)
  );
  set(
    inputtedDate,
    changeDateFormat(
      changedDateTimezone,
      DateFormat.DateMonthYearHourMinuteSecond,
      get(dateInputFormat)
    )
  );

  if (!value) {
    set(dateModel, '');
    set(timeModel, '');
  } else if (
    isValid(value, DateFormat.DateMonthYearHourMinuteSecond, get(seconds))
  ) {
    const [date, time] = changedDateTimezone.split(' ');
    const [day, month, year] = date.split('/');
    const formattedDate = `${year}-${month}-${day}`;
    if (formattedDate !== get(dateModel)) {
      set(dateModel, formattedDate);
    }
    if (time !== get(timeModel)) {
      set(timeModel, time);
    }
  }
}

watch(value, onValueChange);
watch(selectedTimezone, () => onValueChange(get(value)));
onMounted(() => onValueChange(get(value)));

const getDefaultTimezoneName = (offset: number) => {
  let hour = offset / 60;
  if (!Number.isInteger(offset)) hour = 0;

  const isPositive = hour > 0;
  return `Etc/GMT${isPositive ? '+' : ''}hour`;
};

const setCurrentTimezone = () => {
  const guessedTimezone = dayjs.tz.guess();
  const offset = dayjs().utcOffset() / 60;

  const doesTimezoneExist = timezones.filter(
    timezone => timezone === guessedTimezone
  );

  set(
    selectedTimezone,
    doesTimezoneExist ? guessedTimezone : getDefaultTimezoneName(offset)
  );
};

const formatDate = (date: string) => {
  if (!date) return '';

  const [year, month, day] = date.split('-');
  return `${day}/${month}/${year}`;
};

const input = (dateTime: string) => {
  emit('input', dateTime);
};

const emitIfValid = (
  value: string,
  format: DateFormat = get(dateInputFormat)
) => {
  if (isValid(value, format, get(seconds))) {
    const formattedDate = changeDateFormat(
      value,
      format,
      DateFormat.DateMonthYearHourMinuteSecond
    );
    input(
      convertDateByTimezone(
        formattedDate,
        DateFormat.DateMonthYearHourMinuteSecond,
        get(selectedTimezone),
        dayjs.tz.guess()
      )
    );
  }
};

const updateActualDate = () => {
  let value = formatDate(get(dateModel));
  const time = get(timeModel);
  if (time) {
    value += ` ${time}`;
  }

  emitIfValid(value, DateFormat.DateMonthYearHourMinuteSecond);
};

const onTimeChange = (time: string) => {
  set(timeModel, time);
  updateActualDate();
};

const onDateChange = (date: string) => {
  set(dateModel, date);
  updateActualDate();
};

const setNow = () => {
  const now = dayjs();
  set(timeModel, now.format(get(timeFormat)));
  set(dateModel, now.format(defaultDateFormat));
  updateActualDate();
};

const reset = () => {
  const field = get(inputField);
  field?.reset();
};

setCurrentTimezone();

defineExpose({
  reset
});
</script>

<style module lang="scss">
.menu {
  z-index: 999;
  display: flex;
  flex-direction: column;

  > * {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
  }

  :global {
    .v-picker {
      &__title {
        height: 102px;
      }
    }
  }

  &:first-child {
    :global {
      .v-picker {
        border-top-right-radius: 0 !important;
        border-bottom-right-radius: 0 !important;
      }
    }
  }

  &:last-child {
    :global {
      .v-picker {
        border-top-left-radius: 0 !important;
        border-bottom-left-radius: 0 !important;
      }
    }
  }
}
</style>
