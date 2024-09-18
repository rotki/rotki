<script setup lang="ts">
import dayjs from 'dayjs';
import IMask, { type InputMask, MaskedRange } from 'imask';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
import { DateFormat } from '@/types/date-format';
import { toMessages } from '@/utils/validation';
import { timezones } from '@/data/timezones';

const props = withDefaults(
  defineProps<{
    label?: string;
    hint?: string;
    persistentHint?: boolean;
    modelValue: string;
    limitNow?: boolean;
    allowEmpty?: boolean;
    milliseconds?: boolean;
    disabled?: boolean;
    errorMessages?: string[];
    hideDetails?: boolean;
    dateOnly?: boolean;
    inputOnly?: boolean;
    dense?: boolean;
  }>(),
  {
    label: '',
    hint: '',
    persistentHint: false,
    limitNow: false,
    allowEmpty: false,
    milliseconds: false,
    disabled: false,
    errorMessages: () => [],
    hideDetails: false,
    dateOnly: false,
    inputOnly: false,
    dense: false,
  },
);

const emit = defineEmits<{ (e: 'update:model-value', value: string): void }>();

const { allowEmpty, limitNow, errorMessages, milliseconds, dateOnly } = toRefs(props);
const imask = ref<InputMask<any> | null>(null);

const { t } = useI18n();

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const dateOnlyFormat = computed<string>(() => getDateInputISOFormat(get(dateInputFormat)));

const dateTimeFormat = computed<string>(() => `${get(dateOnlyFormat)} HH:mm`);

const dateTimeFormatWithSecond = computed<string>(() => `${get(dateTimeFormat)}:ss`);

const dateTimeFormatWithMilliseconds = computed<string>(() => `${get(dateTimeFormatWithSecond)}.SSS`);

const currentValue = ref<string>('');
const selectedTimezone = ref<string>('');
const inputField = ref();

function isValidFormat(date: string): boolean {
  return (
    isValidDate(date, get(dateOnlyFormat))
    || isValidDate(date, get(dateTimeFormat))
    || isValidDate(date, get(dateTimeFormatWithSecond))
    || (get(milliseconds) && isValidDate(date, get(dateTimeFormatWithMilliseconds)))
  );
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

const dateFormatErrorMessage = computed<string>(() => {
  const dateFormat = get(dateOnlyFormat);
  return get(milliseconds)
    ? t('date_time_picker.milliseconds_format', {
      dateFormat,
    })
    : get(dateOnly)
      ? t('date_time_picker.date_only_format', {
        dateFormat,
      })
      : t('date_time_picker.default_format', {
        dateFormat,
      });
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
    isOnLimit: helpers.withMessage(t('date_time_picker.limit_now'), (v: string): boolean => isDateOnLimit(v)),
  },
  timezone: {
    required: helpers.withMessage(t('date_time_picker.timezone_field.non_empty'), required),
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

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

function onValueChange(value: string) {
  const imaskVal = get(imask)!;

  if (!value && imaskVal)
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

watch(() => props.modelValue, onValueChange);
watch(selectedTimezone, () => onValueChange(props.modelValue));

function input(dateTime: string) {
  emit('update:model-value', dateTime);
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
  const format = get(milliseconds) ? get(dateTimeFormatWithMilliseconds) : get(dateTimeFormatWithSecond);
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
  const convertPattern = (pattern: string) => pattern.replace(/[\s/:]/g, match => `${match}\``);

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
    mask.push(
      {
        mask: convertPattern(get(dateTimeFormat)),
        blocks: {
          ...dateBlocks,
          ...hourAndMinuteBlocks,
        },
        lazy: false,
        overwrite: true,
      },
      {
        mask: convertPattern(get(dateTimeFormatWithSecond)),
        blocks: {
          ...dateBlocks,
          ...hourAndMinuteBlocks,
          ...secondBlocks,
        },
        lazy: false,
        overwrite: true,
      },
    );

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

  newImask.on('accept', () => {
    const unmasked = get(imask)?.unmaskedValue;
    const value = get(imask)?.value;
    const prev = get(currentValue);
    set(currentValue, value);
    if (prev === undefined) {
      // Reset validation when imask just created
      get(v$).$reset();
    }
    if (value && unmasked)
      emitIfValid(value);
  });

  set(imask, newImask);
}

onMounted(() => {
  set(selectedTimezone, guessTimezone());
  initImask();
});

function focus() {
  const inputWrapper = get(inputField)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  nextTick(() => {
    const formattedValue = get(imask)!.value;
    input.value = formattedValue;
    set(currentValue, formattedValue);
  });
}

defineExpose({
  valid: computed(() => !get(v$).$invalid),
});
</script>

<template>
  <RuiTextField
    ref="inputField"
    :model-value="currentValue"
    :label="label"
    :hint="hint"
    :disabled="disabled"
    :hide-details="hideDetails"
    prepend-icon="calendar-line"
    :persistent-hint="persistentHint"
    variant="outlined"
    color="primary"
    :error-messages="toMessages(v$.date)"
    :dense="dense"
    @focus="focus()"
  >
    <template
      v-if="!inputOnly"
      #append
    >
      <RuiMenu
        :popper="{ placement: 'bottom-end' }"
        menu-class="date-time-picker w-[20rem]"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            type="button"
            :disabled="disabled"
            icon
            size="sm"
            class="!p-1.5"
            v-bind="attrs"
          >
            <RuiIcon name="earth-line" />
          </RuiButton>
        </template>

        <RuiAutoComplete
          v-model="selectedTimezone"
          :label="t('date_time_picker.select_timezone')"
          class="!p-4 pb-0"
          variant="outlined"
          :error-messages="toMessages(v$.timezone)"
          :options="timezones"
        />
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
