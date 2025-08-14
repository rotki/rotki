<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, requiredIf } from '@vuelidate/validators';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';
import { toMessages } from '@/utils/validation';

const taxFreeAfterPeriod = ref<string>('');
const taxFreePeriod = ref(false);

const { t } = useI18n({ useScope: 'global' });

const { taxfreeAfterPeriod: period } = storeToRefs(useAccountingSettingsStore());

const rules = {
  taxFreeAfterPeriod: {
    minValue: helpers.withMessage(t('account_settings.validation.tax_free_days_gt_zero'), minValue(1)),
    required: helpers.withMessage(t('account_settings.validation.tax_free_days'), requiredIf(taxFreePeriod)),
  },
};

const v$ = useVuelidate(rules, { taxFreeAfterPeriod }, { $autoDirty: true });

function convertPeriod(period: number, currentType: 'days' | 'seconds') {
  const dayInSeconds = 86400;
  if (currentType === 'days')
    return period * dayInSeconds;
  else if (currentType === 'seconds')
    return period / dayInSeconds;

  throw new Error(`invalid type: ${currentType}`);
}

function getTaxFreePeriod(enabled: boolean) {
  if (!enabled)
    return -1;

  return convertPeriod(365, 'days');
}

function resetTaxFreePeriod() {
  const currentPeriod = get(period);
  if (currentPeriod && currentPeriod > -1) {
    set(taxFreePeriod, true);
    set(taxFreeAfterPeriod, convertPeriod(currentPeriod, 'seconds').toString());
  }
  else {
    set(taxFreePeriod, false);
    set(taxFreeAfterPeriod, undefined);
  }
}

function callIfValid<T = unknown>(value: T, method: (e: T) => void) {
  const validator = get(v$);
  if (!validator.$error)
    method(value);
}

function switchSuccess(enabled: boolean) {
  return t('account_settings.messages.tax_free', {
    enabled: enabled ? 'enabled' : 'disabled',
  });
}

function numberSuccess(period: number) {
  return t('account_settings.messages.tax_free_period', {
    period,
  });
}

function getPeriod(value: number) {
  return value ? convertPeriod(value, 'days') : -1;
}

onMounted(() => {
  resetTaxFreePeriod();
});
</script>

<template>
  <div>
    <SettingsOption
      #default="{ error, success, update }"
      setting="taxfreeAfterPeriod"
      :transform="getTaxFreePeriod"
      :success-message="switchSuccess"
      @finished="resetTaxFreePeriod()"
    >
      <RuiSwitch
        v-model="taxFreePeriod"
        data-cy="taxfree-period-switch"
        :success-messages="success"
        :error-messages="error"
        :label="t('accounting_settings.trade.labels.tax_free')"
        color="primary"
        @update:model-value="update($event)"
      />
    </SettingsOption>

    <SettingsOption
      #default="{ error, success, update }"
      setting="taxfreeAfterPeriod"
      :transform="getPeriod"
      :success-message="numberSuccess"
      @finished="resetTaxFreePeriod()"
    >
      <RuiTextField
        v-model="taxFreeAfterPeriod"
        variant="outlined"
        color="primary"
        data-cy="taxfree-period"
        class="pt-4"
        :success-messages="success"
        :error-messages="error || toMessages(v$.taxFreeAfterPeriod)"
        :disabled="!taxFreePeriod"
        :label="t('accounting_settings.trade.labels.taxfree_after_period')"
        type="number"
        @update:model-value="callIfValid($event, update)"
      />
    </SettingsOption>
  </div>
</template>
