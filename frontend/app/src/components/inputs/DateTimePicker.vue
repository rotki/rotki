<script setup lang="ts">
import dayjs from 'dayjs';
import { type ComputedRef, type Ref } from 'vue';
import IMask, {
  type AnyMaskedOptions,
  type InputMask,
  MaskedRange
} from 'imask';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { timezones } from '@/data/timezones';
import { DateFormat } from '@/types/date-format';
import { toMessages } from '@/utils/validation';

const { t } = useI18n();

const props = withDefaults(
  defineProps<{
    label?: string;
    hint?: string;
    persistentHint?: boolean;
    value?: string;
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

const { seconds, value, allowEmpty, limitNow, errorMessages } = toRefs(props);

const currentValue: Ref<string> = ref('');
const selectedTimezone: Ref<string> = ref('');
const inputField: Ref<any> = ref(null);

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

const dateFormatErrorMessage: ComputedRef<string> = computed(() => {
  const dateFormat = get(dateInputFormatInISO);
  return get(seconds)
    ? t('date_time_picker.seconds_format', {
        dateFormat
      })
    : t('date_time_picker.default_format', {
        dateFormat
      });
});

const rules = {
  date: {
    isValidFormat: helpers.withMessage(
      () => get(dateFormatErrorMessage),
      (v: string): boolean => {
        if (get(allowEmpty) && !v) {
          return true;
        }
        return isValidFormat(v);
      }
    ),
    isOnLimit: helpers.withMessage(
      t('date_time_picker.limit_now'),
      (v: string): boolean => isDateOnLimit(v)
    )
  },
  timezone: {
    required: helpers.withMessage(
      t('date_time_picker.timezone_field.non_empty'),
      required
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    date: currentValue,
    timezone: selectedTimezone
  },
  {
    $autoDirty: true,
    $stopPropagation: true,
    $externalResults: computed(() => ({ date: get(errorMessages) }))
  }
);

const onValueChange = (value: string) => {
  const imaskVal = get(imask)!;

  if (!value) {
    imaskVal.value = '';
  }
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
  set(currentValue, nowInString);
  emitIfValid(nowInString);
};

const css = useCssModule();

const initImask = () => {
  const inputWrapper = get(inputField)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

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
    mask,
    lazy: false
  });

  set(imask, newImask);
};

onMounted(() => {
  setCurrentTimezone();
  initImask();
});

watch(
  () => get(imask)?.value,
  (value, prev) => {
    const unmasked = get(imask)?.unmaskedValue;
    set(currentValue, value);
    if (prev === undefined) {
      // Reset validation when imask just created
      get(v$).$reset();
    }
    if (value && unmasked) {
      emitIfValid(value);
    }
  }
);

const inputted = (event: string) => {
  nextTick(() => {
    get(imask)!.value = event;
  });
};

const focus = () => {
  const inputWrapper = get(inputField)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  nextTick(() => {
    const formattedValue = get(imask)!.value;
    input.value = formattedValue;
    set(currentValue, formattedValue);
  });
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
      :outlined="outlined"
      :error-messages="toMessages(v$.date)"
      @input="inputted($event)"
      @focus="focus()"
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
              :error-messages="toMessages(v$.timezone)"
              :items="timezones"
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
