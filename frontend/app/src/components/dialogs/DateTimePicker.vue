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

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  Ref,
  ref,
  toRefs,
  unref,
  watch
} from '@vue/composition-api';
import dayjs from 'dayjs';
import { setupSettings } from '@/composables/settings';
import { timezones } from '@/data/timezones';
import i18n from '@/i18n';
import { DateFormat } from '@/types/date-format';
import {
  changeDateFormat,
  convertDateByTimezone,
  getDateInputISOFormat,
  isValidDate
} from '@/utils/date';
import { logger } from '@/utils/logging';

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
  const dateFormatRule = (date: string) => {
    const format = unref(dateInputFormat);
    const dateFormat = getDateInputISOFormat(format);

    if (unref(allowEmpty) && !date) {
      return true;
    }

    if (unref(seconds)) {
      return (
        isValid(date, format, true) ||
        i18n
          .t('date_time_picker.seconds_format', {
            dateFormat
          })
          .toString()
      );
    }
    return (
      isValid(date, format) ||
      i18n
        .t('date_time_picker.default_format', {
          dateFormat
        })
        .toString()
    );
  };

  const allRules = computed(() => unref(rules).concat(dateFormatRule));
  const timezoneRule = computed(() => [
    (v: string) =>
      !!v || i18n.t('date_time_picker.timezone_field.non_empty').toString()
  ]);

  return { allRules, timezoneRule };
};

type ValidationRules = ((v: string) => boolean | string)[];

export default defineComponent({
  name: 'DateTimePicker',
  props: {
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
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { dateInputFormat } = setupSettings();

    const { seconds, rules, limitNow, value, allowEmpty } = toRefs(props);
    const timeFormat = computed(() => {
      let format = 'HH:mm';
      if (unref(seconds)) {
        format += ':ss';
      }
      return format;
    });
    const showMenu = ref(false);
    const inputtedDate = ref('');
    const selectedTimezone = ref('');
    const timeModel = ref(dayjs().format(timeFormat.value));
    const dateModel = ref('');
    const inputField = ref();

    const maxDate = computed(() => {
      if (unref(limitNow)) {
        return dayjs().format(defaultDateFormat);
      }
      return '';
    });

    const maxTime = computed(() => {
      if (unref(limitNow) && dayjs(unref(dateModel)).isToday()) {
        return dayjs().format(unref(timeFormat));
      }
      return '';
    });

    function onValueChange(value: string) {
      const changedDateTimezone = convertDateByTimezone(
        value,
        DateFormat.DateMonthYearHourMinuteSecond,
        dayjs.tz.guess(),
        unref(selectedTimezone)
      );
      inputtedDate.value = changeDateFormat(
        changedDateTimezone,
        DateFormat.DateMonthYearHourMinuteSecond,
        unref(dateInputFormat)
      );

      if (!value) {
        dateModel.value = '';
        timeModel.value = '';
      } else if (
        isValid(value, DateFormat.DateMonthYearHourMinuteSecond, unref(seconds))
      ) {
        const [date, time] = changedDateTimezone.split(' ');
        const [day, month, year] = date.split('/');
        const formattedDate = `${year}-${month}-${day}`;
        if (formattedDate !== unref(dateModel)) {
          dateModel.value = formattedDate;
        }
        if (time !== unref(timeModel)) {
          timeModel.value = time;
        }
      }
    }

    watch(value, onValueChange);
    watch(selectedTimezone, () => onValueChange(unref(value)));
    onMounted(() => onValueChange(unref(value)));

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

      selectedTimezone.value = doesTimezoneExist
        ? guessedTimezone
        : getDefaultTimezoneName(offset);
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
      format: DateFormat = unref(dateInputFormat)
    ) => {
      if (isValid(value, format, unref(seconds))) {
        logger.debug(value, format, 'was valid');
        const formattedDate = changeDateFormat(
          value,
          format,
          DateFormat.DateMonthYearHourMinuteSecond
        );
        input(
          convertDateByTimezone(
            formattedDate,
            DateFormat.DateMonthYearHourMinuteSecond,
            unref(selectedTimezone),
            dayjs.tz.guess()
          )
        );
      }
    };

    const updateActualDate = () => {
      let value = formatDate(unref(dateModel));
      const time = unref(timeModel);
      if (time) {
        value += ` ${time}`;
      }

      emitIfValid(value, DateFormat.DateMonthYearHourMinuteSecond);
    };

    const onTimeChange = (time: string) => {
      timeModel.value = time;
      updateActualDate();
    };

    const onDateChange = (date: string) => {
      dateModel.value = date;
      updateActualDate();
    };

    const setNow = () => {
      const now = dayjs();
      timeModel.value = now.format(unref(timeFormat));
      dateModel.value = now.format(defaultDateFormat);
      updateActualDate();
    };

    const reset = () => {
      const field = unref(inputField);
      field?.reset();
    };

    setCurrentTimezone();

    return {
      dateModel,
      timeModel,
      maxDate,
      maxTime,
      inputtedDate,
      selectedTimezone,
      timezones,
      showMenu,
      inputField,
      ...useRules(rules, dateInputFormat, seconds, allowEmpty),
      setNow,
      onTimeChange,
      onDateChange,
      reset,
      emitIfValid
    };
  }
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
