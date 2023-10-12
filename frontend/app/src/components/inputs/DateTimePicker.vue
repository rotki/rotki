<script setup lang="ts">
import dayjs from 'dayjs';
import { type ComputedRef, type Ref, useListeners } from 'vue';
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

const props = withDefaults(
  defineProps<{
    label?: string;
    hint?: string;
    persistentHint?: boolean;
    value?: string;
    limitNow?: boolean;
    allowEmpty?: boolean;
    seconds?: boolean;
    milliseconds?: boolean;
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
    milliseconds: false,
    outlined: false,
    disabled: false,
    errorMessages: () => [],
    hideDetails: false
  }
);

const emit = defineEmits<{ (e: 'input', value: string): void }>();

const { seconds, value, allowEmpty, limitNow, errorMessages, milliseconds } =
  toRefs(props);

const { t } = useI18n();

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

const completeDateTimeFormatWithMilliseconds: ComputedRef<string> = computed(
  () => `${get(dateInputFormatInISO)} HH:mm:ss.SSS`
);

const currentValue: Ref<string> = ref('');
const selectedTimezone: Ref<string> = ref('');
const inputField = ref();

const isValidFormat = (date: string): boolean => {
  const dateFormat = get(dateInputFormatInISO);
  const dateTimeFormatVal = get(dateTimeFormat);
  const completeDateTimeFormatVal = get(completeDateTimeFormat);
  const completeDateTimeFormatWithMillisecondsVal = get(
    completeDateTimeFormatWithMilliseconds
  );

  return (
    isValidDate(date, dateFormat) ||
    isValidDate(date, dateTimeFormatVal) ||
    (!get(seconds) && isValidDate(date, completeDateTimeFormatVal)) ||
    (get(milliseconds) &&
      isValidDate(date, completeDateTimeFormatWithMillisecondsVal))
  );
};

const isDateOnLimit = (date: string): boolean => {
  if (!get(limitNow)) {
    return true;
  }

  const now = dayjs();
  let format: string = get(dateInputFormatInISO);
  if (date.includes(' ')) {
    format += ' HH:mm';
    if (date.charAt(date.length - 6) === ':') {
      format += ':ss';
    }
  }

  const timezone = get(selectedTimezone);

  const dateStringToDate = dayjs
    .tz(date, format, timezone)
    .tz(dayjs.tz.guess());

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
  const now = dayjs().tz(get(selectedTimezone));
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

  const millisecondsBlocks = {
    SSS: createBlock(0, 999)
  };

  // Find every character '/', ':', ' ', and adds '`' character after it.
  // It is used to prevent the character to shift back.
  const convertPattern = (pattern: string) =>
    pattern.replace(new RegExp(/[\s/:]/, 'g'), match => `${match}\``);

  const mask: AnyMaskedOptions[] = [
    {
      mask: convertPattern(get(dateInputFormatInISO)),
      blocks: {
        ...dateBlocks
      },
      lazy: false,
      overwrite: true
    },
    ...(!get(seconds)
      ? [
          {
            mask: convertPattern(get(dateTimeFormat)),
            blocks: {
              ...dateBlocks,
              ...hourAndMinuteBlocks
            },
            lazy: false,
            overwrite: true
          }
        ]
      : []),
    {
      mask: convertPattern(get(completeDateTimeFormatVal)),
      blocks: {
        ...dateBlocks,
        ...hourAndMinuteBlocks,
        ...secondBlocks
      },
      lazy: false,
      overwrite: true
    },
    ...(get(milliseconds)
      ? [
          {
            mask: convertPattern(get(completeDateTimeFormatWithMilliseconds)),
            blocks: {
              ...dateBlocks,
              ...hourAndMinuteBlocks,
              ...secondBlocks,
              ...millisecondsBlocks
            },
            lazy: false,
            overwrite: true
          }
        ]
      : [])
  ];

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

const focus = () => {
  const inputWrapper = get(inputField)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  nextTick(() => {
    const formattedValue = get(imask)!.value;
    input.value = formattedValue;
    set(currentValue, formattedValue);
  });
};

const listeners = useListeners();

const filteredListeners = (listeners: any) => ({
  ...listeners,
  input: () => {}
});
</script>

<template>
  <VTextField
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
    @focus="focus()"
    v-on="filteredListeners(listeners)"
  >
    <template #append>
      <VMenu
        :close-on-content-click="false"
        transition="scale-transition"
        :nudge-bottom="56"
        left
        max-width="580px"
        class="date-time-picker"
      >
        <template #activator="{ on }">
          <VBtn icon class="mt-n2" v-on="on">
            <VIcon>mdi-earth</VIcon>
          </VBtn>
        </template>

        <div :class="css.menu">
          <VAutocomplete
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
      </VMenu>
      <VBtn
        data-cy="date-time-picker__set-now-button"
        icon
        class="mt-n2"
        @click="setNow()"
      >
        <VIcon>mdi-clock-outline</VIcon>
      </VBtn>
    </template>
  </VTextField>
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
