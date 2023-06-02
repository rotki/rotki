<script setup lang="ts">
import dayjs from 'dayjs';
import { type ComputedRef, type Ref } from 'vue';
import IMask, {
  type AnyMaskedOptions,
  type InputMask,
  MaskedRange
} from 'imask';
import { timezones } from '@/data/timezones';
import { DateFormat } from '@/types/date-format';

const isValidFormat = (date: string): boolean => {
  const dateFormat = get(dateInputFormatInISO);
  const dateTimeFormatVal = get(dateTimeFormat);
  const completeDateTimeFormatVal = get(completeDateTimeFormat);

  return (
    isValidDate(date, dateFormat) ||
    isValidDate(date, dateTimeFormatVal) ||
    (!get(seconds) && isValidDate(date, completeDateTimeFormatVal))
  );
};

const isDateOnLimit = (date: string): boolean => {
  if (!get(limitNow)) {
    return true;
  }

  const now = dayjs();
  const dateStringToDate = dayjs(
    convertToTimestamp(date, get(dateInputFormat)) * 1000
  );

  return !dateStringToDate.isAfter(now);
};

const isValid = (date: string): boolean =>
  isValidFormat(date) && isDateOnLimit(date);

const useRules = (rules: Ref<ValidationRules>) => {
  const { t } = useI18n();
  const dateFormatRule = (date: string) => {
    const dateFormat = get(dateInputFormatInISO);

    if (get(allowEmpty) && !date) {
      return true;
    }

    return (
      isValidFormat(date) ||
      (get(seconds)
        ? t('date_time_picker.seconds_format', {
            dateFormat
          })
        : t('date_time_picker.default_format', {
            dateFormat
          }))
    );
  };

  const dateLimitRule = (date: string) =>
    isDateOnLimit(date) || t('date_time_picker.limit_now');

  const allRules = computed(() =>
    get(rules).concat(dateFormatRule, dateLimitRule)
  );
  const timezoneRule = computed(() => [
    (v: string) =>
      !!v || t('date_time_picker.timezone_field.non_empty').toString()
  ]);

  return { allRules, timezoneRule };
};

type ValidationRules = ((v: string) => boolean | string)[];

const props = withDefaults(
  defineProps<{
    label?: string;
    hint?: string;
    persistentHint?: boolean;
    value?: string;
    rules?: ValidationRules;
    limitNow?: boolean;
    allowEmpty?: boolean;
    seconds?: boolean;
    outlined?: boolean;
    disabled?: boolean;
    errorMessages?: string[];
    hideDetails?: boolean;
  }>(),
  {
    label: '',
    hint: '',
    persistentHint: false,
    value: '',
    rules: () => [],
    limitNow: false,
    allowEmpty: false,
    seconds: false,
    outlined: false,
    disabled: false,
    errorMessages: () => [],
    hideDetails: false
  }
);

const emit = defineEmits<{ (e: 'input', value: string): void }>();

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const dateInputFormatInISO: ComputedRef<string> = computed(() =>
  getDateInputISOFormat(get(dateInputFormat))
);

const timeFormat = computed(() => {
  let format = 'HH:mm';
  if (get(seconds)) {
    format += ':ss';
  }
  return format;
});

const dateTimeFormat: ComputedRef<string> = computed(
  () => `${get(dateInputFormatInISO)} ${get(timeFormat)}`
);

const completeDateTimeFormat: ComputedRef<string> = computed(
  () => `${get(dateInputFormatInISO)} HH:mm:ss`
);

const { seconds, rules, value, allowEmpty, limitNow } = toRefs(props);

const { allRules, timezoneRule } = useRules(rules);

const currentValue = ref('');
const selectedTimezone = ref('');
const inputField = ref();

const onValueChange = (value: string) => {
  const changedDateTimezone = convertDateByTimezone(
    value,
    DateFormat.DateMonthYearHourMinuteSecond,
    dayjs.tz.guess(),
    get(selectedTimezone)
  );

  const newValue = changeDateFormat(
    changedDateTimezone,
    DateFormat.DateMonthYearHourMinuteSecond,
    get(dateInputFormat)
  );

  const imaskVal = get(imask);
  if (imaskVal) {
    imaskVal.value = newValue;
    set(currentValue, newValue);
  }
};

watch(value, onValueChange);
watch(selectedTimezone, () => onValueChange(get(value)));

const imask: Ref<InputMask<any> | null> = ref(null);

const getDefaultTimezoneName = (offset: number) => {
  let hour = offset / 60;
  if (!Number.isInteger(offset)) {
    hour = 0;
  }

  const isPositive = hour > 0;
  return `Etc/GMT${isPositive ? '+' : ''}hour`;
};

const setCurrentTimezone = () => {
  const guessedTimezone = dayjs.tz.guess();
  const offset = dayjs().utcOffset() / 60;
  const doesTimezoneExist = timezones.find(
    timezone => timezone === guessedTimezone
  );

  set(selectedTimezone, doesTimezoneExist ?? getDefaultTimezoneName(offset));
};

const input = (dateTime: string) => {
  emit('input', dateTime);
};

const emitIfValid = (value: string) => {
  if (isValid(value)) {
    const changedDateTimezone = convertDateByTimezone(
      value,
      get(dateInputFormat),
      get(selectedTimezone),
      dayjs.tz.guess()
    );

    const formattedValue = changeDateFormat(
      changedDateTimezone,
      get(dateInputFormat),
      DateFormat.DateMonthYearHourMinuteSecond
    );

    input(formattedValue);
  }
};

const setNow = () => {
  const now = dayjs();
  const nowInString = now.format(get(dateTimeFormat));
  emitIfValid(nowInString);
};

const reset = () => {
  const field = get(inputField);
  field?.reset();
};

defineExpose({
  reset
});

const css = useCssModule();

const initImask = () => {
  const inputWrapper = get(inputField) as any;
  const input = inputWrapper.$el.querySelector('input') as HTMLElement;

  const completeDateTimeFormatVal = get(completeDateTimeFormat);

  const createBlock = (from: number, to: number) => ({
    mask: MaskedRange,
    from,
    to
  });

  const dateBlocks = {
    YYYY: createBlock(1970, 9999),
    MM: createBlock(1, 12),
    DD: createBlock(1, 31)
  };

  const hourAndMinuteBlocks = {
    HH: createBlock(0, 23),
    mm: createBlock(0, 59)
  };

  const secondBlocks = {
    ss: createBlock(0, 59)
  };

  const mask: AnyMaskedOptions[] = [
    {
      mask: get(dateInputFormatInISO),
      blocks: {
        ...dateBlocks
      },
      lazy: false
    },
    {
      mask: get(completeDateTimeFormatVal),
      blocks: {
        ...dateBlocks,
        ...hourAndMinuteBlocks,
        ...secondBlocks
      },
      lazy: false
    }
  ];

  if (!get(seconds)) {
    mask.splice(1, 0, {
      mask: get(dateTimeFormat),
      blocks: {
        ...dateBlocks,
        ...hourAndMinuteBlocks
      },
      lazy: false
    });
  }

  const newImask = IMask(input, {
    mask
  });

  set(imask, newImask);
};

onMounted(() => {
  setCurrentTimezone();
  initImask();
});

watch(
  () => get(imask)?.value,
  value => {
    if (value) {
      set(currentValue, value);
      emitIfValid(value);
    }
  }
);

const inputted = (emittedValue: string) => {
  const current = get(currentValue);
  set(currentValue, emittedValue);
  emitIfValid(emittedValue);

  // revert back if inputted value exceed the max length allowed.
  const sanitized = emittedValue.replace(/_/g, '');
  if (sanitized.length > 19) {
    nextTick(() => {
      set(currentValue, current);
      emitIfValid(current);
    });
  }
};
</script>

<template>
  <div>
    <v-text-field
      ref="inputField"
      :value="currentValue"
      :label="label"
      :hint="hint"
      :disabled="disabled"
      :hide-details="hideDetails"
      prepend-inner-icon="mdi-calendar"
      :persistent-hint="persistentHint"
      :rules="allRules"
      :outlined="outlined"
      :error-messages="errorMessages"
      @input="inputted($event)"
    >
      <template #append>
        <v-menu
          :close-on-content-click="false"
          transition="scale-transition"
          :nudge-bottom="56"
          left
          max-width="580px"
          class="date-time-picker"
        >
          <template #activator="{ on }">
            <v-btn icon class="mt-n2" v-on="on">
              <v-icon>mdi-earth</v-icon>
            </v-btn>
          </template>

          <div :class="css.menu">
            <v-autocomplete
              v-model="selectedTimezone"
              label="Select timezone"
              class="pa-4 pb-0"
              outlined
              persistent-hint
              menu-pros="auto"
              :items="timezones"
              :rules="timezoneRule"
            />
          </div>
        </v-menu>
        <v-btn
          data-cy="date-time-picker__set-now-button"
          icon
          class="mt-n2"
          @click="setNow()"
        >
          <v-icon>mdi-clock-outline</v-icon>
        </v-btn>
      </template>
    </v-text-field>
  </div>
</template>

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
