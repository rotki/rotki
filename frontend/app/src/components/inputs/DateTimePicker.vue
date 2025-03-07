<script setup lang="ts">
import { timezones } from '@/data/timezones';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { DateFormat } from '@/types/date-format';
import { changeDateFormat, convertDateByTimezone, getDateInputISOFormat, guessTimezone, isValidDate } from '@/utils/date';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';
import IMask, { type InputMask, MaskedRange } from 'imask';

interface DateTimePickerProps {
  label?: string;
  hint?: string;
  persistentHint?: boolean;
  limitNow?: boolean;
  allowEmpty?: boolean;
  milliseconds?: boolean;
  disabled?: boolean;
  errorMessages?: string[] | string;
  hideDetails?: boolean;
  dateOnly?: boolean;
  inputOnly?: boolean;
  hideTimezoneSelector?: boolean;
  dense?: boolean;
}

const modelValue = defineModel<string>({ required: true });

const props = withDefaults(defineProps<DateTimePickerProps>(), {
  allowEmpty: false,
  dateOnly: false,
  dense: false,
  disabled: false,
  errorMessages: () => [],
  hideDetails: false,
  hideTimezoneSelector: false,
  hint: '',
  inputOnly: false,
  label: '',
  limitNow: false,
  milliseconds: false,
  persistentHint: false,
});

const { allowEmpty, dateOnly, errorMessages, limitNow, milliseconds } = toRefs(props);
const iMask = ref<InputMask<any>>();

const { t } = useI18n();

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const dateOnlyFormat = computed<string>(() => getDateInputISOFormat(get(dateInputFormat)));

const dateTimeFormat = computed<string>(() => `${get(dateOnlyFormat)} HH:mm`);

const dateTimeFormatWithSecond = computed<string>(() => `${get(dateTimeFormat)}:ss`);

const dateTimeFormatWithMilliseconds = computed<string>(() => `${get(dateTimeFormatWithSecond)}.SSS`);

const currentValue = ref<string>('');
const selectedTimezone = ref<string>(guessTimezone());
const inputField = ref();

const dateFormatErrorMessage = computed<string>(() => {
  const dateFormat = get(dateOnlyFormat);
  if (get(milliseconds)) {
    return t('date_time_picker.milliseconds_format', {
      dateFormat,
    });
  }
  else if (get(dateOnly)) {
    return t('date_time_picker.date_only_format', {
      dateFormat,
    });
  }
  else {
    return t('date_time_picker.default_format', {
      dateFormat,
    });
  }
});

const rules = {
  date: {
    isFormatValid: helpers.withMessage(
      () => get(dateFormatErrorMessage),
      (v: string): boolean => {
        if (get(allowEmpty) && (!v || !/\d/.test(v)))
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

const v$ = useVuelidate(rules, {
  date: currentValue,
  timezone: selectedTimezone,
}, {
  $autoDirty: true,
  $externalResults: computed(() => ({ date: get(errorMessages) })),
  $stopPropagation: true,
});

function isValidFormat(date: string): boolean {
  return (
    isValidDate(date, get(dateOnlyFormat))
    || isValidDate(date, get(dateTimeFormat))
    || isValidDate(date, get(dateTimeFormatWithSecond))
    || (get(milliseconds) && isValidDate(date, get(dateTimeFormatWithMilliseconds)))
  );
}

function isDateOnLimit(date: string): boolean {
  if (!get(limitNow) || !isValidFormat(date))
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

function updateIMaskValue(value: string) {
  if (!isDefined(iMask)) {
    return;
  }
  nextTick(() => {
    get(iMask).value = value;
  });
}

function convertToUserDateFormat(value: string) {
  const millisecondsVal = get(milliseconds);
  const changedDateTimezone = convertDateByTimezone(
    value,
    DateFormat.DateMonthYearHourMinuteSecond,
    guessTimezone(),
    get(selectedTimezone),
    millisecondsVal,
  );

  return changeDateFormat(
    changedDateTimezone,
    DateFormat.DateMonthYearHourMinuteSecond,
    get(dateInputFormat),
    millisecondsVal,
  );
}

function onValueChange(value: string) {
  if (!value && isDefined(iMask)) {
    updateIMaskValue('');
  }
  const newValue = convertToUserDateFormat(value);

  if (isDefined(iMask)) {
    updateIMaskValue(newValue);
    set(currentValue, newValue);
  }
}

function emitIfValid(value: string) {
  if (!isValid(value)) {
    return;
  }
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
  set(modelValue, formattedValue);
}

function setNow() {
  const now = dayjs().tz(get(selectedTimezone));
  const format = get(milliseconds) ? get(dateTimeFormatWithMilliseconds) : get(dateTimeFormatWithSecond);
  const nowInString = now.format(format);
  set(currentValue, nowInString);
  emitIfValid(nowInString);
}

function initIMask() {
  const inputWrapper = get(inputField)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  const createBlock = (from: number, to: number) => ({
    from,
    mask: MaskedRange,
    to,
  });

  const dateBlocks = {
    DD: createBlock(1, 31),
    MM: createBlock(1, 12),
    YYYY: createBlock(1970, 9999),
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
      blocks: {
        ...dateBlocks,
      },
      lazy: false,
      mask: convertPattern(get(dateOnlyFormat)),
      overwrite: true,
    },
  ];

  if (!get(dateOnly)) {
    mask.push(
      {
        blocks: {
          ...dateBlocks,
          ...hourAndMinuteBlocks,
        },
        lazy: false,
        mask: convertPattern(get(dateTimeFormat)),
        overwrite: true,
      },
      {
        blocks: {
          ...dateBlocks,
          ...hourAndMinuteBlocks,
          ...secondBlocks,
        },
        lazy: false,
        mask: convertPattern(get(dateTimeFormatWithSecond)),
        overwrite: true,
      },
    );

    if (get(milliseconds)) {
      mask.push({
        blocks: {
          ...dateBlocks,
          ...hourAndMinuteBlocks,
          ...secondBlocks,
          ...millisecondsBlocks,
        },
        lazy: false,
        mask: convertPattern(get(dateTimeFormatWithMilliseconds)),
        overwrite: true,
      });
    }
  }

  const newIMask = IMask(input, {
    mask,
  });

  if (isDefined(modelValue)) {
    nextTick(() => {
      const value = convertToUserDateFormat(get(modelValue));
      newIMask.value = value;
      set(currentValue, value);
    });
  }

  newIMask.on('accept', () => {
    const unmasked = get(iMask)?.unmaskedValue;
    const value = get(iMask)?.value;
    const prev = get(currentValue);
    set(currentValue, value);
    if (prev === undefined) {
      // Reset validation when iMask just created
      get(v$).$reset();
    }
    if (value && unmasked)
      emitIfValid(value);
  });

  set(iMask, newIMask);
}

function focus() {
  const inputWrapper = get(inputField)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  nextTick(() => {
    const formattedValue = get(iMask)!.value;
    input.value = formattedValue;
    set(currentValue, formattedValue);
  });
}

watch(modelValue, onValueChange);
watch(selectedTimezone, () => onValueChange(get(modelValue)));
watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

onMounted(() => {
  initIMask();
});

onBeforeUnmount(() => {
  get(iMask)?.destroy();
  set(iMask, undefined);
});

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
    prepend-icon="lu-calendar-days"
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
        v-if="!hideTimezoneSelector"
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
            v-bind="{ ...attrs, tabIndex: -1 }"
          >
            <RuiIcon name="lu-earth" />
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
        :tabindex="-1"
        icon
        size="sm"
        class="!p-1.5"
        @click="setNow()"
      >
        <RuiIcon name="lu-map-pin-check-inside" />
      </RuiButton>
    </template>
  </RuiTextField>
</template>
