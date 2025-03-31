<script setup lang="ts">
import { timezones } from '@/data/timezones';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import {
  convertFromTimestamp,
  convertTimestampByTimezone,
  convertToTimestamp,
  getDateInputISOFormat,
  guessTimezone,
  isValidDate,
} from '@/utils/date';
import { toMessages } from '@/utils/validation';
import { RuiAutoComplete, RuiCalendar, RuiTextField } from '@rotki/ui-library';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import dayjs, { type Dayjs } from 'dayjs';
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
  dense?: boolean;
  minValue?: number;
  maxValue?: number;
}

const rawModelValue = defineModel<number>({ required: true });

const props = withDefaults(defineProps<DateTimePickerProps>(), {
  allowEmpty: false,
  dateOnly: false,
  dense: false,
  disabled: false,
  errorMessages: () => [],
  hideDetails: false,
  hint: '',
  inputOnly: false,
  label: '',
  limitNow: false,
  milliseconds: false,
  persistentHint: false,
});

const { allowEmpty, dateOnly, errorMessages, limitNow, maxValue, milliseconds, minValue } = toRefs(props);
const iMask = ref<InputMask<any>>();

const { t } = useI18n();

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const dateOnlyFormat = computed<string>(() => getDateInputISOFormat(get(dateInputFormat)));
const dateTimeFormat = computed<string>(() => `${get(dateOnlyFormat)} HH:mm`);
const dateTimeFormatWithSecond = computed<string>(() => `${get(dateTimeFormat)}:ss`);
const dateTimeFormatWithMilliseconds = computed<string>(() => `${get(dateTimeFormatWithSecond)}.SSS`);

const currentValue = ref<string>('');
const selectedTimezone = ref<string>(guessTimezone());
const inputFieldRef = useTemplateRef<InstanceType<typeof RuiTextField>>('inputFieldRef');
const datePickerRef = useTemplateRef<InstanceType<typeof RuiCalendar>>('datePickerRef');
const menuContainerRef = useTemplateRef<InstanceType<typeof HTMLDivElement>>('menuContainerRef');
const timeZoneAutoCompleteRef = ref();

const open = ref<boolean>(false);
const timezoneMenu = ref<boolean>(false);
const lastPageUpdate = ref<number>(0);
const lastPageTitle = ref<string>('');
const now = ref<Dayjs>(dayjs());

const inputElement = computed(() => get(inputFieldRef)?.$el);
const { focused: inputFocused } = useFocusWithin(inputElement);
const { focused: menuFocusedWithin } = useFocusWithin(menuContainerRef);
const { focused: menuFocused } = useFocus(menuContainerRef);

const anyFocused = computed(() => get(inputFocused) || get(menuFocusedWithin) || (get(timezoneMenu)));
const debouncedAnyFocused = debouncedRef(anyFocused, 100);
const usedAnyFocused = logicOr(anyFocused, debouncedAnyFocused);

function normalizeTimestamp(timestamp: number, multiply = false) {
  const ms = get(milliseconds);
  if (ms) {
    return timestamp;
  }
  if (multiply) {
    return timestamp * 1000;
  }
  return Math.floor(timestamp / 1000);
}

// Model value adjusted to the timezone
const modelValue = computed({
  get() {
    const value = get(rawModelValue);
    if (!value) {
      return value;
    }

    return convertTimestampByTimezone(value, guessTimezone(), get(selectedTimezone), get(milliseconds));
  },
  set(value: number) {
    if (!value) {
      set(rawModelValue, value);
    }

    set(rawModelValue, convertTimestampByTimezone(value, get(selectedTimezone), guessTimezone(), get(milliseconds)));
  },
});

const dateModel = computed({
  get() {
    const val = get(modelValue);
    if (!val) {
      return undefined;
    }
    return new Date(normalizeTimestamp(val, true));
  },
  set(value: Date | null) {
    if (!value) {
      set(modelValue, 0);
    }
    else {
      set(modelValue, normalizeTimestamp(value.getTime()));
    }
  },
});

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

  set(now, dayjs());
  let format: string = get(dateOnlyFormat);
  if (date.includes(' ')) {
    format += ' HH:mm';
    if (date.at(-6) === ':')
      format += ':ss';
  }

  const timezone = get(selectedTimezone);
  const dateStringToDate = dayjs.tz(date, format, timezone).tz(guessTimezone());
  return !dateStringToDate.isAfter(get(now));
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

function onValueChange() {
  const value = get(modelValue);
  const newValue = value ? convertFromTimestamp(value, get(dateInputFormat), get(milliseconds)) : '';
  updateIMaskValue(newValue);
  set(currentValue, newValue);
}

function emitIfValid(value: string) {
  if (!isValid(value)) {
    return;
  }

  const timestamp = convertToTimestamp(value, get(dateInputFormat), get(milliseconds));
  set(modelValue, timestamp);
}

function setNow() {
  set(now, dayjs());
  const timestamp = get(now).tz(get(selectedTimezone));
  const format = get(milliseconds) ? get(dateTimeFormatWithMilliseconds) : get(dateTimeFormatWithSecond);
  const nowInString = timestamp.format(format);
  set(currentValue, nowInString);
  emitIfValid(nowInString);
}

const maxDate = computed(() => {
  const nowVal = get(now);
  const propMaxValue = get(maxValue);
  const max = propMaxValue ? normalizeTimestamp(propMaxValue, true) : Infinity;
  const nowValue = get(limitNow) && nowVal ? nowVal.valueOf() : Infinity;

  const compared = Math.min(max, nowValue);
  return compared === Infinity ? undefined : compared;
});

const minDate = computed(() => {
  const min = get(minValue);
  if (min) {
    return normalizeTimestamp(min, true);
  }
  return undefined;
});

function resetTimezone() {
  set(selectedTimezone, guessTimezone());
}

function initIMask() {
  const inputWrapper = get(inputElement)!;
  const input = inputWrapper.querySelector('input') as HTMLInputElement;

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
      onValueChange();
    });
  }

  newIMask.on('accept', () => {
    const unmasked = get(iMask)?.unmaskedValue;
    const value = get(iMask)?.value;
    const prev = get(currentValue);
    set(currentValue, value);
    if (!isDefined(prev)) {
      // Reset validation when iMask just created
      get(v$).$reset();
    }
    if (value && unmasked)
      emitIfValid(value);
  });

  set(iMask, newIMask);
}

function openMenu() {
  set(open, true);
}

function updatePages(event: { title: string }[]) {
  const title = event[0]?.title;
  if (title && title !== get(lastPageTitle)) {
    set(lastPageTitle, title);
    set(lastPageUpdate, dayjs().valueOf());
  }
}

watch(modelValue, onValueChange);

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

watch([dateModel, open], ([model, open]) => {
  if (open) {
    get(datePickerRef)?.move(model || new Date());
  }
});

watch(timezoneMenu, (curr) => {
  if (!curr) {
    set(menuFocused, true);
  }
});

watch(usedAnyFocused, (curr, prev) => {
  if (prev && !curr) {
    const last = get(lastPageUpdate);
    if (last) {
      const now = dayjs().valueOf();
      if (now - last >= 800) {
        set(open, false);
      }
      else {
        set(lastPageUpdate, 0);
        set(menuFocused, true);
      }
    }
    else {
      set(open, false);
    }
  }
});

onMounted(initIMask);

onBeforeUnmount(() => {
  get(iMask)?.destroy();
  set(iMask, undefined);
});

defineExpose({
  open,
  valid: computed(() => !get(v$).$invalid),
});
</script>

<template>
  <RuiMenu
    :model-value="open"
    persist-on-activator-click
    wrapper-class="w-full"
    :disabled="disabled"
    persistent
    :popper="{
      offsetDistance: 8 - (!hideDetails ? 24 : 0),
    }"
  >
    <template #activator="{ attrs }">
      <RuiTextField
        v-bind="attrs"
        ref="inputFieldRef"
        class="w-full"
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
        @update:model-value="openMenu()"
        @focus="openMenu()"
      >
        <template #append>
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="transition-all"
            :class="{ 'rotate-180': open }"
            @click="open = !open"
          >
            <RuiIcon name="lu-chevron-down" />
          </RuiButton>
        </template>
      </RuiTextField>
    </template>
    <div
      ref="menuContainerRef"
      class="flex"
      tabindex="-1"
    >
      <RuiCalendar
        ref="datePickerRef"
        v-model="dateModel"
        borderless
        :max-date="maxDate"
        :min-date="minDate"
        :allow-empty="allowEmpty"
        @update:pages="updatePages($event)"
      />
      <RuiTimePicker
        v-model="dateModel"
        class="border-l border-default"
        borderless
        :accuracy="milliseconds ? 'millisecond' : 'second'"
      />
      <div class="border-l border-default">
        <div class="flex border-b border-default gap-1 p-2">
          <RuiTooltip
            :open-delay="200"
            :popper="{ placement: 'top' }"
          >
            <template #activator>
              <RuiButton
                icon
                variant="text"
                type="button"
                size="sm"
                class="!p-1.5"
                @click="open = false"
              >
                <RuiIcon name="lu-chevron-up" />
              </RuiButton>
            </template>
            {{ t('date_time_picker.close') }}
          </RuiTooltip>

          <RuiTooltip
            v-if="allowEmpty"
            :open-delay="200"
            :popper="{ placement: 'top' }"
          >
            <template #activator>
              <RuiButton
                icon
                variant="text"
                color="error"
                type="button"
                size="sm"
                class="!p-1.5"
                @click="modelValue = 0"
              >
                <RuiIcon name="lu-delete" />
              </RuiButton>
            </template>
            {{ t('date_time_picker.clear_value') }}
          </RuiTooltip>

          <template v-if="!inputOnly">
            <RuiMenu
              v-model="timezoneMenu"
              :popper="{ placement: 'top' }"
              menu-class="date-time-picker w-[20rem]"
            >
              <template #activator="{ attrs }">
                <RuiTooltip
                  :open-delay="200"
                  :popper="{ placement: 'top' }"
                >
                  <template #activator>
                    <RuiButton
                      variant="text"
                      icon
                      size="sm"
                      class="!p-1.5"
                      v-bind="{ ...attrs, tabIndex: -1 }"
                    >
                      <RuiIcon name="lu-globe" />
                    </RuiButton>
                  </template>
                  {{ t('date_time_picker.select_timezone') }}
                </RuiTooltip>
              </template>

              <div
                class="flex p-4 gap-2"
                tabindex="-1"
              >
                <RuiAutoComplete
                  ref="timeZoneAutoCompleteRef"
                  v-model="selectedTimezone"
                  :label="t('date_time_picker.select_timezone')"
                  variant="outlined"
                  hide-details
                  dense
                  :error-messages="toMessages(v$.timezone)"
                  :options="timezones"
                />

                <RuiButton
                  variant="text"
                  color="primary"
                  size="sm"
                  class="!px-2"
                  @click="resetTimezone()"
                >
                  <RuiIcon
                    name="lu-refresh-ccw"
                    size="16"
                  />
                </RuiButton>
              </div>
            </RuiMenu>

            <RuiTooltip
              :open-delay="200"
              :popper="{ placement: 'top' }"
            >
              <template #activator>
                <RuiButton
                  data-cy="date-time-picker__set-now-button"
                  variant="text"
                  type="button"
                  :tabindex="-1"
                  icon
                  size="sm"
                  class="!p-1.5"
                  @click="setNow()"
                >
                  <RuiIcon name="lu-map-pin-check-inside" />
                </RuiButton>
              </template>
              {{ t('date_time_picker.set_to_current_time') }}
            </RuiTooltip>
          </template>
        </div>
        <div class="pt-2">
          <RuiButton
            variant="list"
            class="w-full !py-2 !px-4"
          >
            Today
          </RuiButton>
          <RuiButton
            variant="list"
            class="w-full !py-2 !px-4"
          >
            Yesterday
          </RuiButton>
          <RuiButton
            variant="list"
            class="w-full !py-2 !px-4"
          >
            Last Week
          </RuiButton>
          <RuiButton
            variant="list"
            class="w-full !py-2 !px-4"
          >
            Last Month
          </RuiButton>
          <RuiButton
            variant="list"
            class="w-full !py-2 !px-4"
          >
            Last 6 Months
          </RuiButton>
          <RuiButton
            variant="list"
            class="w-full !py-2 !px-4"
          >
            Last Year
          </RuiButton>
        </div>
      </div>
    </div>
  </RuiMenu>
</template>
