<script setup lang="ts">
import { bigNumberify } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, maxValue, minValue } from '@vuelidate/validators';
import { storeToRefs } from 'pinia';
import AmountInput from '@/components/inputs/AmountInput.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { toMessages } from '@/utils/validation';

defineProps<{
  disabled: boolean;
}>();

const SECONDS_PER_HOUR = 3600;

const { t } = useI18n({ useScope: 'global' });

const { assetMovementAmountTolerance, assetMovementTimeRange } = storeToRefs(useGeneralSettingsStore());

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
  set(tolerancePercentage, decimalToPercentage(get(assetMovementAmountTolerance)));
}

function resetTimeRangeState(): void {
  set(timeRangeHours, secondsToHours(get(assetMovementTimeRange)));
}

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
            class="!rounded-l-none !px-2 h-9"
          >
            <RuiIcon
              name="lu-settings"
              size="20"
            />
          </RuiButton>
        </template>
        <span>{{ t('asset_movement_matching.settings.tooltip') }}</span>
      </RuiTooltip>
    </template>
    <div class="p-4">
      <div class="text-subtitle-1 font-medium mb-4">
        {{ t('asset_movement_matching.settings.title') }}
      </div>
      <SettingsOption
        #default="{ update, error, success }"
        setting="assetMovementAmountTolerance"
        :transform="percentageToDecimal"
        @finished="resetToleranceState()"
      >
        <AmountInput
          v-model="tolerancePercentage"
          variant="outlined"
          type="number"
          step="0.001"
          :label="t('asset_movement_matching.settings.amount_tolerance.label')"
          :hint="t('asset_movement_matching.settings.amount_tolerance.hint')"
          :error-messages="error || toMessages(v$.tolerancePercentage)"
          :success-messages="success"
          class="min-h-[12rem]"
          @update:model-value="callIfValid($event, update)"
        />
      </SettingsOption>
      <SettingsOption
        #default="{ update, error, success }"
        setting="assetMovementTimeRange"
        :transform="hoursToSeconds"
        @finished="resetTimeRangeState()"
      >
        <AmountInput
          v-model="timeRangeHours"
          variant="outlined"
          integer
          class="min-h-[8rem]"
          :label="t('asset_movement_matching.settings.time_range.label')"
          :hint="t('asset_movement_matching.settings.time_range.hint')"
          :error-messages="error || toMessages(v$.timeRangeHours)"
          :success-messages="success"
          @update:model-value="callIfValid($event, update)"
        />
      </SettingsOption>
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
