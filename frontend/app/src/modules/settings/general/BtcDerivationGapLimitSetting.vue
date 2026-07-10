<script setup lang="ts">
import { Defaults } from '@/modules/core/common/defaults';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });

function successMessage(limit: number): string {
  return t('general_settings.validation.btc_derivation_gap.success', { limit });
}
</script>

<template>
  <SettingNumber
    setting="btcDerivationGapLimit"
    :label="t('general_settings.labels.btc_derivation_gap')"
    :default="Defaults.BTC_DERIVATION_GAP_LIMIT"
    :error-message="t('general_settings.validation.btc_derivation_gap.error')"
    :success-message="successMessage"
  />
</template>
