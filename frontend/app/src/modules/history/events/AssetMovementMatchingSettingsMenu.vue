<script setup lang="ts">
import type { ZodType } from 'zod';
import { bigNumberify } from '@rotki/common';
import { parseNumericInput } from '@/modules/core/common/data/bignumbers';
import {
  checkSetting,
  type MatchingSettingsMessages,
  timeRangeHoursSchema,
  tolerancePercentageSchema,
} from '@/modules/history/events/asset-movement-matching-settings';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

defineProps<{
  disabled: boolean;
  isPinned?: boolean;
}>();

const SECONDS_PER_HOUR = 3600;

const { t } = useI18n({ useScope: 'global' });

const {
  error: toleranceWriteError,
  model: toleranceModel,
  success: toleranceWriteSuccess,
} = useSettingModel('assetMovementAmountTolerance', { debounce: 1500 });
const {
  clearAll: clearTolerance,
  error: toleranceError,
  setError: setToleranceError,
  setSuccess: setToleranceSuccess,
  success: toleranceSuccess,
} = useClearableMessages();

const {
  error: timeRangeWriteError,
  model: timeRangeModel,
  success: timeRangeWriteSuccess,
} = useSettingModel('assetMovementTimeRange', { debounce: 1500 });
const {
  clearAll: clearTimeRange,
  error: timeRangeError,
  setError: setTimeRangeError,
  setSuccess: setTimeRangeSuccess,
  success: timeRangeSuccess,
} = useClearableMessages();

const showMenu = ref<boolean>(false);
const tolerancePercentage = ref<string>('');
const timeRangeHours = ref<string>('');

const messages: MatchingSettingsMessages = {
  timeRangeMin: t('asset_movement_matching.settings.time_range.validations.min'),
  toleranceMax: t('asset_movement_matching.settings.amount_tolerance.validations.max'),
  toleranceMin: t('asset_movement_matching.settings.amount_tolerance.validations.min'),
};

const toleranceRuleErrors = computed<string[]>(
  () => checkSetting(tolerancePercentageSchema(messages), get(tolerancePercentage)),
);
const timeRangeRuleErrors = computed<string[]>(
  () => checkSetting(timeRangeHoursSchema(messages), get(timeRangeHours)),
);

/**
 * Writes the setting only when the value it was given is one the backend takes.
 *
 * Each field answers for itself. The rule it replaces asked the whole validator whether anything
 * was wrong, so an out-of-range tolerance stopped the time range from saving too, and the two have
 * nothing to do with each other.
 *
 * The schemas deliberately pass a field that holds nothing yet, since the menu writes on every
 * keystroke, so a value that is not a number is stopped here instead: converting one writes NaN
 * seconds, or throws on the way to a decimal.
 */
function writeIfValid(value: string, schema: ZodType<string>, write: (value: string) => void): void {
  if (!parseNumericInput(value))
    return;

  if (checkSetting(schema, value).length === 0)
    write(value);
}

function decimalToPercentage(decimal: string): string {
  const value = bigNumberify(decimal);
  return value.multipliedBy(100).toString();
}

function percentageToDecimal(percentage: string): string {
  const value = bigNumberify(percentage);
  return value.dividedBy(100).toString();
}

function secondsToHours(seconds: number): string {
  return (seconds / SECONDS_PER_HOUR).toString();
}

function hoursToSeconds(hours: string): number {
  return Math.round(Number.parseFloat(hours) * SECONDS_PER_HOUR);
}

function resetToleranceState(): void {
  set(tolerancePercentage, decimalToPercentage(get(toleranceModel)));
}

function resetTimeRangeState(): void {
  set(timeRangeHours, secondsToHours(get(timeRangeModel)));
}

function updateTolerance(value: string): void {
  set(toleranceModel, percentageToDecimal(value));
}

function updateTimeRange(value: string): void {
  set(timeRangeModel, hoursToSeconds(value));
}

watch(toleranceModel, () => {
  clearTolerance();
});

watch(toleranceWriteSuccess, (saved) => {
  if (saved) {
    setToleranceSuccess('', true);
    resetToleranceState();
  }
});

watch(toleranceWriteError, (message) => {
  if (message) {
    setToleranceError(message, true);
    resetToleranceState();
  }
});

watch(timeRangeModel, () => {
  clearTimeRange();
});

watch(timeRangeWriteSuccess, (saved) => {
  if (saved) {
    setTimeRangeSuccess('', true);
    resetTimeRangeState();
  }
});

watch(timeRangeWriteError, (message) => {
  if (message) {
    setTimeRangeError(message, true);
    resetTimeRangeState();
  }
});

onMounted(() => {
  resetToleranceState();
  resetTimeRangeState();
});
</script>

<template>
  <RuiMenu
    v-model="showMenu"
    menu-class="w-full max-w-96"
    :popper="{ placement: 'bottom-end' }"
    :disabled="disabled"
    class="!border-l-0"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            v-bind="attrs"
            :disabled="disabled"
            icon
            :size="isPinned ? 'sm' : 'lg'"
            class="!rounded-l-none"
            :class="{ 'h-[30px]': isPinned }"
          >
            <RuiIcon name="lu-settings" />
          </RuiButton>
        </template>
        <span>{{ t('asset_movement_matching.settings.tooltip') }}</span>
      </RuiTooltip>
    </template>
    <div class="p-4">
      <div class="text-subtitle-1 font-medium mb-4">
        {{ t('asset_movement_matching.settings.title') }}
      </div>
      <AmountInput
        v-model="tolerancePercentage"
        variant="outlined"
        type="number"
        step="0.001"
        :label="t('asset_movement_matching.settings.amount_tolerance.label')"
        :hint="t('asset_movement_matching.settings.amount_tolerance.hint')"
        :error-messages="toleranceError || toleranceRuleErrors"
        :success-messages="toleranceSuccess"
        class="min-h-[12rem]"
        @update:model-value="writeIfValid($event, tolerancePercentageSchema(messages), updateTolerance)"
      />
      <AmountInput
        v-model="timeRangeHours"
        variant="outlined"
        integer
        class="min-h-[8rem]"
        :label="t('asset_movement_matching.settings.time_range.label')"
        :hint="t('asset_movement_matching.settings.time_range.hint')"
        :error-messages="timeRangeError || timeRangeRuleErrors"
        :success-messages="timeRangeSuccess"
        @update:model-value="writeIfValid($event, timeRangeHoursSchema(messages), updateTimeRange)"
      />
      <div class="flex justify-end mt-4">
        <RuiButton
          variant="text"
          color="primary"
          @click="showMenu = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>
