<script setup lang="ts">
import { CurrencyLocation } from '@/modules/assets/amount-display/currency-location';
import SettingSelect from '@/modules/settings/controls/SettingSelect.vue';

const { t } = useI18n({ useScope: 'global' });

const options = [CurrencyLocation.BEFORE, CurrencyLocation.AFTER];

function successMessage(currencyLocation: string): string {
  return t('general_settings.validation.currency_location.success', { currencyLocation });
}
</script>

<template>
  <SettingSelect
    control="radio"
    setting="currencyLocation"
    class="flex flex-col"
    data-testid="currency-location-input"
    :options="options"
    :error-message="t('general_settings.validation.currency_location.error')"
    :success-message="successMessage"
  >
    <template #option="{ option }">
      <template v-if="option === CurrencyLocation.BEFORE">
        {{ t('general_settings.amount.label.location_before') }}
        <div class="text-sm text-rui-text-secondary mt-1">
          {{ t('general_settings.amount.example.before') }}
        </div>
      </template>
      <template v-else>
        {{ t('general_settings.amount.label.location_after') }}
        <div class="text-sm text-rui-text-secondary mt-1">
          {{ t('general_settings.amount.example.after') }}
        </div>
      </template>
    </template>
  </SettingSelect>
</template>
