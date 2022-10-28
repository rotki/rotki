<template>
  <div>
    <settings-option
      #default="{ error, success, update }"
      setting="taxfreeAfterPeriod"
      :transform="getTaxFreePeriod"
      :success-message="switchSuccess"
      @finished="resetTaxFreePeriod"
    >
      <v-switch
        v-model="taxFreePeriod"
        class="accounting-settings__taxfree-period"
        :success-messages="success"
        :error-messages="error"
        :label="tc('accounting_settings.labels.tax_free')"
        color="primary"
        @change="update"
      />
    </settings-option>

    <settings-option
      #default="{ error, success, update }"
      setting="taxfreeAfterPeriod"
      :transform="getPeriod"
      :success-message="numberSuccess"
      @finished="resetTaxFreePeriod"
    >
      <v-text-field
        v-model="taxFreeAfterPeriod"
        outlined
        class="accounting-settings__taxfree-period-days pt-4"
        :success-messages="success"
        :error-messages="
          error || v$.taxFreeAfterPeriod.$errors.map(e => e.$message)
        "
        :disabled="!taxFreePeriod"
        :label="tc('accounting_settings.labels.tax_free_period')"
        type="number"
        @change="callIfValid($event, update)"
      />
    </settings-option>
  </div>
</template>

<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const taxFreeAfterPeriod = ref<number | null>(null);
const taxFreePeriod = ref(false);

const { tc } = useI18n();

const { taxfreeAfterPeriod: period } = storeToRefs(
  useAccountingSettingsStore()
);

const rules = {
  taxFreeAfterPeriod: {
    required: helpers.withMessage(
      tc('account_settings.validation.tax_free_days'),
      required
    ),
    minValue: helpers.withMessage(
      tc('account_settings.validation.tax_free_days_gt_zero'),
      minValue(1)
    )
  }
};

const v$ = useVuelidate(rules, { taxFreeAfterPeriod }, { $autoDirty: true });

const convertPeriod = (period: number, currentType: 'days' | 'seconds') => {
  const dayInSeconds = 86400;
  if (currentType === 'days') {
    return period * dayInSeconds;
  } else if (currentType === 'seconds') {
    return period / dayInSeconds;
  }
  throw new Error(`invalid type: ${currentType}`);
};

const getTaxFreePeriod = (enabled: boolean) => {
  if (!enabled) {
    return -1;
  }

  return convertPeriod(365, 'days');
};

const resetTaxFreePeriod = () => {
  const currentPeriod = get(period);
  if (currentPeriod && currentPeriod > -1) {
    set(taxFreePeriod, true);
    set(taxFreeAfterPeriod, convertPeriod(currentPeriod, 'seconds'));
  } else {
    set(taxFreePeriod, false);
    set(taxFreeAfterPeriod, null);
  }
};

const callIfValid = <T = unknown>(value: T, method: (e: T) => void) => {
  const validator = get(v$);
  if (!validator.$error) {
    method(value);
  }
};

const switchSuccess = (enabled: boolean) =>
  tc('account_settings.messages.tax_free', 0, {
    enabled: enabled ? 'enabled' : 'disabled'
  });

const numberSuccess = (period: number) =>
  tc('account_settings.messages.tax_free_period', 0, {
    period
  });

const getPeriod = (value: number) =>
  value ? convertPeriod(value, 'days') : -1;

onMounted(() => {
  resetTaxFreePeriod();
});
</script>
