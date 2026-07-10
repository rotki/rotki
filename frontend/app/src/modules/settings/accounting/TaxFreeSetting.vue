<script setup lang="ts">
import SettingToggleNumber from '@/modules/settings/controls/SettingToggleNumber.vue';

const DAY_IN_SECONDS = 86400;

const { t } = useI18n({ useScope: 'global' });

function toDays(seconds: number): string {
  return (seconds / DAY_IN_SECONDS).toString();
}

function toSeconds(days: string): number {
  return Number.parseInt(days) * DAY_IN_SECONDS;
}

function switchSuccess(enabled: boolean): string {
  return t('account_settings.messages.tax_free', { enabled: enabled ? 'enabled' : 'disabled' });
}

function numberSuccess(period: string): string {
  return t('account_settings.messages.tax_free_period', { period });
}
</script>

<template>
  <SettingToggleNumber
    setting="taxfreeAfterPeriod"
    :enabled-value="365 * DAY_IN_SECONDS"
    :min="1"
    :to-field="toDays"
    :from-field="toSeconds"
    :switch-label="t('accounting_settings.trade.labels.tax_free')"
    :field-label="t('accounting_settings.trade.labels.taxfree_after_period')"
    :validation="{
      empty: t('account_settings.validation.tax_free_days'),
      invalid: t('account_settings.validation.tax_free_days_gt_zero'),
    }"
    :success="{ onToggle: switchSuccess, onValue: numberSuccess }"
    switch-test-id="taxfree-period-switch"
    field-test-id="taxfree-period"
  />
</template>
