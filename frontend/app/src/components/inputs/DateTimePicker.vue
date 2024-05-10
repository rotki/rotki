<script setup lang="ts">
import dayjs from 'dayjs';
import IMask, { type InputMask, MaskedRange } from 'imask';
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
    disabled?: boolean;
    errorMessages?: string[];
    hideDetails?: boolean;
    dateOnly?: boolean;
    inputOnly?: boolean;
  }>(),
  {
    label: '',
    hint: '',
    persistentHint: false,
    value: '',
    limitNow: false,
    allowEmpty: false,
    milliseconds: false,
    disabled: false,
    errorMessages: () => [],
    hideDetails: false,
    dateOnly: false,
    inputOnly: false,
  },
);

const emit = defineEmits<{ (e: 'input', value: string): void }>();

const { value, allowEmpty, limitNow, errorMessages, milliseconds, dateOnly } = toRefs(props);

const imask: Ref<InputMask<any> | null> = ref(null);

const { t } = useI18n();

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const dateOnlyFormat: ComputedRef<string> = computed(() =>
  getDateInputISOFormat(get(dateInputFormat)),
);

const dateTimeFormat: ComputedRef<string> = computed(
  () => `${get(dateOnlyFormat)} HH:mm`,
);

const dateTimeFormatWithSecond: ComputedRef<string> = computed(
  () => `${get(dateTimeFormat)}:ss`,
);

const dateTimeFormatWithMilliseconds: ComputedRef<string> = computed(
  () => `${get(dateTimeFormatWithSecond)}.SSS`,
);

const currentValue: Ref<string> = ref('');
const selectedTimezone: Ref<string> = ref('');
const inputField = ref();

function isValidFormat(date: string): boolean {
  return isValidDate(date, get(dateOnlyFormat))
    || isValidDate(date, get(dateTimeFormat))
    || isValidDate(date, get(dateTimeFormatWithSecond))
    || (get(milliseconds) && isValidDate(date, get(dateTimeFormatWithMilliseconds)));
}

function isDateOnLimit(date: string): boolean {
  if (!get(limitNow))
    return true;

  const now = dayjs();
  let format: string = get(dateOnlyFormat);
  if (date.includes(' ')) {
    format += ' HH:mm';
    if (date.at(-6) === ':')
      format += ':ss';
  }

  const timezone = get(selectedTimezone);

  const dateStringToDate = dayjs.tz(date, format, timezone).tz(guessTimezone());

  return !dateStringToDate.isAfter(now);
}

function isValid(date: string): boolean {
  return isValidFormat(date) && isDateOnLimit(date);
}

const dateFormatErrorMessage: ComputedRef<string> = computed(() => {
  const dateFormat = get(dateOnlyFormat);
  return get(milliseconds)
    ? t('date_time_picker.milliseconds_format', {
      dateFormat,
    })
    : (
        get(dateOnly)
          ? t('date_time_picker.date_only_format', {
            dateFormat,
          })
          : t('date_time_picker.default_format', {
            dateFormat,
          })
      );
});

const rules = {
  date: {
    isValidFormat: helpers.withMessage(
      () => get(dateFormatErrorMessage),
      (v: string): boolean => {
        if (get(allowEmpty) && !v)
          return true;

        return isValidFormat(v);
      },
    ),
    isOnLimit: helpers.withMessage(
      t('date_time_picker.limit_now'),
      (v: string): boolean => isDateOnLimit(v),
    ),
  },
  timezone: {
    required: helpers.withMessage(
      t('date_time_picker.timezone_field.non_empty'),
      required,
    ),
  },
};

const v$ = useVuelidate(
  rules,
  {
    date: currentValue,
    timezone: selectedTimezone,
  },
  {
    $autoDirty: true,
    $stopPropagation: true,
    $externalResults: computed(() => ({ date: get(errorMessages) })),
  },
);

function onValueChange(value: string) {
  const imaskVal = get(imask)!;

  if (!value)
    imaskVal.value = '';

  const millisecondsVal = get(milliseconds);
  const changedDateTimezone = convertDateByTimezone(
    value,
    DateFormat.DateMonthYearHourMinuteSecond,
    guessTimezone(),
    get(selectedTimezone),
    millisecondsVal,
  );

  const newValue = changeDateFormat(
    changedDateTimezone,
    DateFormat.DateMonthYearHourMinuteSecond,
    get(dateInputFormat),
    millisecondsVal,
  );

  if (imaskVal) {
    imaskVal.value = newValue;
    set(currentValue, newValue);
  }
}

watch(value, onValueChange);
watch(selectedTimezone, () => onValueChange(get(value)));

function input(dateTime: string) {
  emit('input', dateTime);
}

function emitIfValid(value: string) {
  if (isValid(value)) {
    const changedDateTimezone = convertDateByTimezone(
      value,
      get(dateInputFormat),
      get(selectedTimezone),
      guessTimezone(),
      get(milliseconds),
    );

    const formattedValue = changeDateFormat(
      changedDateTimezone,
      get(dateInputFormat),
      DateFormat.DateMonthYearHourMinuteSecond,
      get(milliseconds),
    );

    input(formattedValue);
  }
}

function setNow() {
  const now = dayjs().tz(get(selectedTimezone));
  const format = get(milliseconds)
    ? get(dateTimeFormatWithMilliseconds)
    : get(dateTimeFormatWithSecond);
  const nowInString = now.format(format);
  set(currentValue, nowInString);
  emitIfValid(nowInString);
}

function initImask() {
  const inputWrapper = get(inputField)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  const createBlock = (from: number, to: number) => ({
    mask: MaskedRange,
    from,
    to,
  });

  const dateBlocks = {
    YYYY: createBlock(1970, 9999),
    MM: createBlock(1, 12),
    DD: createBlock(1, 31),
  };

  const hourAndMinuteBlocks = {
    HH: createBlock(0, 23),
    mm: createBlock(0, 59),
  };

  const secondBlocks = {
    ss: createBlock(0, 59),
  };

  const millisecondsBlocks = {
    SSS: createBlock(0, 999),
  };

  // Find every character '/', ':', ' ', and adds '`' character after it.
  // It is used to prevent the character to shift back.
  const convertPattern = (pattern: string) =>
    pattern.replace(/[\s/:]/g, match => `${match}\``);

  const mask = [
    {
      mask: convertPattern(get(dateOnlyFormat)),
      blocks: {
        ...dateBlocks,
      },
      lazy: false,
      overwrite: true,
    },
  ];

  if (!get(dateOnly)) {
    mask.push({
      mask: convertPattern(get(dateTimeFormat)),
      blocks: {
        ...dateBlocks,
        ...hourAndMinuteBlocks,
      },
      lazy: false,
      overwrite: true,
    }, {
      mask: convertPattern(get(dateTimeFormatWithSecond)),
      blocks: {
        ...dateBlocks,
        ...hourAndMinuteBlocks,
        ...secondBlocks,
      },
      lazy: false,
      overwrite: true,
    });

    if (get(milliseconds)) {
      mask.push({
        mask: convertPattern(get(dateTimeFormatWithMilliseconds)),
        blocks: {
          ...dateBlocks,
          ...hourAndMinuteBlocks,
          ...secondBlocks,
          ...millisecondsBlocks,
        },
        lazy: false,
        overwrite: true,
      });
    }
  }

  const newImask = IMask(input, {
    mask,
  });

  set(imask, newImask);
}

onMounted(() => {
  set(selectedTimezone, guessTimezone());
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
    if (value && unmasked)
      emitIfValid(value);
  },
);

function focus() {
  const inputWrapper = get(inputField)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  nextTick(() => {
    const formattedValue = get(imask)!.value;
    input.value = formattedValue;
    set(currentValue, formattedValue);
  });
}

function filteredListeners(listeners: any) {
  return {
    ...listeners,
    input: () => {},
  };
}
</script>

<template>
  <RuiTextField
    ref="inputField"
    :value="currentValue"
    :label="label"
    :hint="hint"
    :disabled="disabled"
    :hide-details="hideDetails"
    prepend-icon="calendar-line"
    :persistent-hint="persistentHint"
    variant="outlined"
    color="primary"
    :error-messages="toMessages(v$.date)"
    @focus="focus()"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      filteredListeners($listeners)
    "
  >
    <template
      v-if="!inputOnly"
      #append
    >
      <RuiMenu
        :popper="{ placement: 'bottom-end' }"
        menu-class="date-time-picker max-w-[32rem] z-[500]"
      >
        <template #activator="{ on }">
          <RuiButton
            variant="text"
            type="button"
            :disabled="disabled"
            icon
            size="sm"
            class="!p-1.5"
            v-on="on"
          >
            <RuiIcon name="earth-line" />
          </RuiButton>
        </template>

        <AppBridge>
          <VAutocomplete
            v-model="selectedTimezone"
            :label="t('date_time_picker.select_timezone')"
            class="!p-4 pb-0"
            outlined
            persistent-hint
            menu-pros="auto"
            :error-messages="toMessages(v$.timezone)"
            :items="timezones"
          />
        </AppBridge>
      </RuiMenu>
      <RuiButton
        data-cy="date-time-picker__set-now-button"
        variant="text"
        type="button"
        :disabled="disabled"
        icon
        size="sm"
        class="!p-1.5"
        @click="setNow()"
      >
        <RuiIcon name="map-pin-time-line" />
      </RuiButton>
    </template>
  </RuiTextField>
</template>
