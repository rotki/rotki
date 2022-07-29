<template>
  <div>
    <settings-option
      #default="{ error, success, update }"
      setting="taxfreeAfterPeriod"
      :transform="getTaxFreePeriod"
      :success-message="
        enabled =>
          $tc('account_settings.messages.tax_free', 0, {
            enabled: enabled ? 'enabled' : 'disabled'
          })
      "
      @finished="resetTaxFreePeriod"
    >
      <v-switch
        v-model="taxFreePeriod"
        class="accounting-settings__taxfree-period"
        :success-messages="success"
        :error-messages="error"
        :label="$tc('accounting_settings.labels.tax_free')"
        color="primary"
        @change="update"
      />
    </settings-option>

    <settings-option
      #default="{ error, success, update }"
      setting="taxfreeAfterPeriod"
      :transform="value => (value ? convertPeriod(value, 'days') : -1)"
      :success-message="
        period =>
          $tc('account_settings.messages.tax_free_period', 0, {
            period
          })
      "
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
        :label="$tc('accounting_settings.labels.tax_free_period')"
        type="number"
        @change="callIfValid($event, update)"
      />
    </settings-option>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';
import i18n from '@/i18n';

const taxFreeAfterPeriod = ref<number | null>(null);
const taxFreePeriod = ref(false);
const { accountingSettings } = useSettings();

const rules = {
  taxFreeAfterPeriod: {
    required: helpers.withMessage(
      i18n.tc('account_settings.validation.tax_free_days'),
      required
    ),
    minValue: helpers.withMessage(
      i18n.tc('account_settings.validation.tax_free_days_gt_zero'),
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
  const settings = get(accountingSettings);
  const period = settings.taxfreeAfterPeriod;

  if (period && period > -1) {
    set(taxFreePeriod, true);
    set(taxFreeAfterPeriod, convertPeriod(period, 'seconds'));
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

onMounted(() => {
  resetTaxFreePeriod();
});
</script>
