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
      <currency-location-setting />

      <div>
        <strong>
          {{ t('general_settings.amount.label.resulting_format') }}
        </strong>
        <amount-display :value="amountExample" show-currency="symbol" />
      </div>

      <rounding-settings />
    </setting-category>
    <ethereum-rpc-node-manager />
    <rpc-settings />
    <price-oracle-settings />
    <frontend-settings />
  </div>
</template>

<script setup lang="ts">
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import RoundingSettings from '@/components/settings/explorers/RoundingSettings.vue';
import FrontendSettings from '@/components/settings/FrontendSettings.vue';
import BalanceSaveFrequencySetting from '@/components/settings/general/BalanceSaveFrequencySetting.vue';
import BtcDerivationGapLimitSetting from '@/components/settings/general/BtcDerivationGapLimitSetting.vue';
import CurrencyLocationSetting from '@/components/settings/general/CurrencyLocationSetting.vue';
import DateDisplayFormatSetting from '@/components/settings/general/DateDisplayFormatSetting.vue';
import DateInputFormatSetting from '@/components/settings/general/DateInputFormatSetting.vue';
import DisplayDateInLocaltimeSetting from '@/components/settings/general/DisplayDateInLocaltimeSetting.vue';
import FloatingPrecisionSetting from '@/components/settings/general/FloatingPrecisionSetting.vue';
import LanguageSetting from '@/components/settings/general/language/LanguageSetting.vue';
import MainCurrencySetting from '@/components/settings/general/MainCurrencySetting.vue';
import NumericSeparatorsSettings from '@/components/settings/general/NumericSeparatorsSettings.vue';
import EthereumRpcNodeManager from '@/components/settings/general/rpc/EthereumRpcNodeManager.vue';
import RpcSettings from '@/components/settings/general/rpc/RpcSettings.vue';
import TreatEthAsEth2Setting from '@/components/settings/general/TreatEthAsEth2Setting.vue';
import UsageAnalyticsSetting from '@/components/settings/general/UsageAnalyticsSetting.vue';
import VersionUpdateFrequencySetting from '@/components/settings/general/VersionUpdateFrequencySetting.vue';
import PriceOracleSettings from '@/components/settings/PriceOracleSettings.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { bigNumberify } from '@/utils/bignumbers';

const amountExample = bigNumberify(123456.789);
const { t } = useI18n();
</script>
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
