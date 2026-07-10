<script setup lang="ts">
import { bigNumberify } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, maxValue, minValue } from '@vuelidate/validators';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
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

const rules = {
  timeRangeHours: {
    min: helpers.withMessage(t('asset_movement_matching.settings.time_range.validations.min'), minValue(1)),
  },
  tolerancePercentage: {
    max: helpers.withMessage(t('asset_movement_matching.settings.amount_tolerance.validations.max'), maxValue(100)),
    min: helpers.withMessage(t('asset_movement_matching.settings.amount_tolerance.validations.min'), minValue(0.0001)),
  },
};

const v$ = useVuelidate(rules, { timeRangeHours, tolerancePercentage }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

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
        :error-messages="toleranceError || toMessages(v$.tolerancePercentage)"
        :success-messages="toleranceSuccess"
        class="min-h-[12rem]"
        @update:model-value="callIfValid($event, updateTolerance)"
      />
      <AmountInput
        v-model="timeRangeHours"
        variant="outlined"
        integer
        class="min-h-[8rem]"
        :label="t('asset_movement_matching.settings.time_range.label')"
        :hint="t('asset_movement_matching.settings.time_range.hint')"
        :error-messages="timeRangeError || toMessages(v$.timeRangeHours)"
        :success-messages="timeRangeSuccess"
        @update:model-value="callIfValid($event, updateTimeRange)"
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
