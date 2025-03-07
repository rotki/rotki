<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import { Defaults } from '@/data/defaults';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';

const DEFAULT_FREQUENCY = Defaults.BALANCE_SAVE_FREQUENCY;

const balanceSaveFrequency = ref<string>(DEFAULT_FREQUENCY.toString());

const { balanceSaveFrequency: frequency } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();

const maxBalanceSaveFrequency = Constraints.MAX_HOURS_DELAY;
const rules = {
  balanceSaveFrequency: {
    between: helpers.withMessage(
      t('general_settings.balance_frequency.validation.invalid_frequency', {
        end: maxBalanceSaveFrequency,
        start: 1,
      }),
      between(1, maxBalanceSaveFrequency),
    ),
    required: helpers.withMessage(t('general_settings.balance_frequency.validation.non_empty'), required),
  },
};
const v$ = useVuelidate(rules, { balanceSaveFrequency }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function resetBalanceSaveFrequency() {
  set(balanceSaveFrequency, get(frequency).toString());
}

function transform(value?: string) {
  return value ? Number.parseInt(value) : value;
}

function successMessage(frequency: string) {
  return t('general_settings.balance_frequency.validation.success', {
    frequency,
  });
}

function reset(update: (value: number) => void): void {
  update(DEFAULT_FREQUENCY);
  set(balanceSaveFrequency, DEFAULT_FREQUENCY.toString());
}

onMounted(() => {
  resetBalanceSaveFrequency();
});
</script>

<template>
  <SettingsOption
    setting="balanceSaveFrequency"
    :transform="transform"
    :error-message="t('general_settings.balance_frequency.validation.error')"
    :success-message="successMessage"
    @finished="resetBalanceSaveFrequency()"
  >
    <template #title>
      {{ t('general_settings.balance_frequency.title') }}
    </template>
    <template #default="{ error, success, update, updateImmediate }">
      <div class="flex items-start w-full">
        <RuiTextField
          v-model="balanceSaveFrequency"
          variant="outlined"
          color="primary"
          min="1"
          :max="maxBalanceSaveFrequency"
          data-cy="balance-save-frequency-input"
          class="w-full"
          :label="t('general_settings.balance_frequency.label')"
          type="number"
          :success-messages="success"
          :error-messages="error || toMessages(v$.balanceSaveFrequency)"
          @update:model-value="callIfValid($event, update)"
        />

        <RuiButton
          class="mt-1 ml-2"
          variant="text"
          icon
          @click="reset(updateImmediate)"
        >
          <RuiIcon name="lu-history" />
        </RuiButton>
      </div>
    </template>
  </SettingsOption>
</template>
