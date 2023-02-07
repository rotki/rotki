<script setup lang="ts">
import { bigNumberify } from '@/utils/bignumbers';

const amountExample = bigNumberify(123456.789);
const { t } = useI18n();
</script>

<template>
  <div class="general-settings mt-n8">
    <setting-category>
      <template #title>
        {{ t('general_settings.title') }}
      </template>

      <usage-analytics-setting />
      <language-setting class="mb-6" />
      <version-update-frequency-setting />
      <balance-save-frequency-setting />
      <date-display-format-setting />
      <date-input-format-setting />
      <display-date-in-localtime-setting />
      <btc-derivation-gap-limit-setting />
      <treat-eth-as-eth2-setting />
    </setting-category>

    <setting-category>
      <template #title>
        {{ t('general_settings.amount.title') }}
      </template>

      <floating-precision-setting />
      <main-currency-setting />
      <numeric-separators-settings />
      <abbreviate-number-setting />
      <currency-location-setting />

      <div>
        <strong>
          {{ t('general_settings.amount.label.resulting_format') }}
        </strong>
        <amount-display :value="amountExample" show-currency="symbol" />
      </div>

      <rounding-settings />
    </setting-category>
    <rpc-settings />
    <price-oracle-settings />
    <frontend-settings />
  </div>
</template>
<style scoped lang="scss">
.general-settings {
  &__currency-list {
    font-size: 2em;
    font-weight: bold;
  }

  &__timeframe {
    min-height: 55px;
  }

  &__date-restore {
    margin-top: -6px;
  }
}
</style>
