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
    milliseconds: false,
    outlined: false,
    disabled: false,
    errorMessages: () => [],
    hideDetails: false
  }
);

const emit = defineEmits<{ (e: 'input', value: string): void }>();

const { value, allowEmpty, limitNow, errorMessages, milliseconds } =
  toRefs(props);

const { t } = useI18n();

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const dateOnlyFormat: ComputedRef<string> = computed(() =>
  getDateInputISOFormat(get(dateInputFormat))
);

const dateTimeFormat: ComputedRef<string> = computed(
  () => `${get(dateOnlyFormat)} HH:mm`
);

const dateTimeFormatWithSecond: ComputedRef<string> = computed(
  () => `${get(dateTimeFormat)}:ss`
);

const dateTimeFormatWithMilliseconds: ComputedRef<string> = computed(
  () => `${get(dateTimeFormatWithSecond)}.SSS`
);

const currentValue: Ref<string> = ref('');
const selectedTimezone: Ref<string> = ref('');
const inputField = ref();

const isValidFormat = (date: string): boolean =>
  isValidDate(date, get(dateOnlyFormat)) ||
  isValidDate(date, get(dateTimeFormat)) ||
  isValidDate(date, get(dateTimeFormatWithSecond)) ||
  (get(milliseconds) && isValidDate(date, get(dateTimeFormatWithMilliseconds)));

const isDateOnLimit = (date: string): boolean => {
  if (!get(limitNow)) {
    return true;
  }

  const now = dayjs();
  let format: string = get(dateOnlyFormat);
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
  const dateFormat = get(dateOnlyFormat);
  return get(milliseconds)
    ? t('date_time_picker.milliseconds_format', {
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
  const millisecondsVal = get(milliseconds);
  const changedDateTimezone = convertDateByTimezone(
    value,
    DateFormat.DateMonthYearHourMinuteSecond,
    dayjs.tz.guess(),
    get(selectedTimezone),
    millisecondsVal
  );

  const newValue = changeDateFormat(
    changedDateTimezone,
    DateFormat.DateMonthYearHourMinuteSecond,
    get(dateInputFormat),
    millisecondsVal
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
      dayjs.tz.guess(),
      get(milliseconds)
    );

    const formattedValue = changeDateFormat(
      changedDateTimezone,
      get(dateInputFormat),
      DateFormat.DateMonthYearHourMinuteSecond,
      get(milliseconds)
    );

    input(formattedValue);
  }
};

const setNow = () => {
  const now = dayjs().tz(get(selectedTimezone));
  const format = get(milliseconds)
    ? get(dateTimeFormatWithMilliseconds)
    : get(dateTimeFormatWithSecond);
  const nowInString = now.format(format);
  set(currentValue, nowInString);
  emitIfValid(nowInString);
};

const css = useCssModule();

const initImask = () => {
  const inputWrapper = get(inputField)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

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
      mask: convertPattern(get(dateOnlyFormat)),
      blocks: {
        ...dateBlocks
      },
      lazy: false,
      overwrite: true
    },
    {
      mask: convertPattern(get(dateTimeFormat)),
      blocks: {
        ...dateBlocks,
        ...hourAndMinuteBlocks
      },
      lazy: false,
      overwrite: true
    },
    {
      mask: convertPattern(get(dateTimeFormatWithSecond)),
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
            mask: convertPattern(get(dateTimeFormatWithMilliseconds)),
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
          <RuiButton
            variant="text"
            type="button"
            icon
            size="sm"
            class="-mt-2 !p-1.5"
            v-on="on"
          >
            <RuiIcon name="earth-line" />
          </RuiButton>
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
      <RuiButton
        data-cy="date-time-picker__set-now-button"
        variant="text"
        type="button"
        icon
        size="sm"
        class="-mt-2 !p-1.5"
        @click="setNow()"
      >
        <RuiIcon name="time-line" />
      </RuiButton>
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
