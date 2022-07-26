<template>
  <div class="general-settings mt-n8">
    <setting-category>
      <template #title>
        {{ $t('general_settings.title') }}
      </template>

      <settings-option
        #default="{ error, success, update }"
        setting="submitUsageAnalytics"
        :error-message="$tc('general_settings.validation.analytics.error')"
      >
        <v-switch
          v-model="anonymousUsageAnalytics"
          class="general-settings__fields__anonymous-usage-statistics mb-4 mt-0"
          color="primary"
          :label="$t('general_settings.labels.anonymous_analytics')"
          :success-messages="success"
          :error-messages="error"
          @change="update($event)"
        />
      </settings-option>

      <version-update-frequency-setting />
      <balance-save-frequency-setting />
      <date-display-format-setting />
      <date-input-format-setting />

      <settings-option
        #default="{ error, success, update }"
        setting="displayDateInLocaltime"
        :error-message="
          $tc('general_settings.validation.display_date_in_localtime.error')
        "
      >
        <v-switch
          v-model="displayDateInLocaltime"
          class="general-settings__fields__display-date-in-localtime mb-4 mt-0"
          color="primary"
          :label="$t('general_settings.labels.display_date_in_localtime')"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="btcDerivationGapLimit"
        :error-message="
          $tc('general_settings.validation.btc_derivation_gap.error')
        "
        :success-message="
          limit =>
            $tc('general_settings.validation.btc_derivation_gap.success', 0, {
              limit
            })
        "
      >
        <v-text-field
          v-model.number="btcDerivationGapLimit"
          outlined
          class="general-settings__fields__btc-derivation-gap"
          :label="$t('general_settings.labels.btc_derivation_gap')"
          type="number"
          :success-messages="success"
          :error-messages="error"
          @change="update($event ? parseInt($event) : $event)"
        />
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="treatEth2AsEth"
        :error-message="
          $tc('general_settings.validation.treat_eth2_as_eth.error')
        "
      >
        <v-switch
          v-model="treatEth2asEth"
          class="general-settings__fields__treat-eth2-as-eth mb-2 mt-0"
          color="primary"
          :label="$t('general_settings.labels.treat_eth2_as_eth')"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>
    </setting-category>

    <setting-category>
      <template #title>
        {{ $t('general_settings.amount.title') }}
      </template>

      <floating-precision-setting />

      <settings-option
        #default="{ error, success, update }"
        setting="mainCurrency"
        :error-message="$tc('general_settings.validation.currency.error')"
        :success-message="
          symbol =>
            $tc('general_settings.validation.currency.success', 0, {
              symbol
            })
        "
      >
        <v-select
          v-model="selectedCurrency"
          outlined
          class="general-settings__fields__currency-selector"
          :label="$t('general_settings.amount.labels.main_currency')"
          item-text="tickerSymbol"
          return-object
          :items="currencies"
          :success-messages="success"
          :error-messages="error"
          @change="update($event ? $event.tickerSymbol : $event)"
        >
          <template #item="{ item, attrs, on }">
            <v-list-item
              :id="`currency__${item.tickerSymbol.toLocaleLowerCase()}`"
              v-bind="attrs"
              v-on="on"
            >
              <v-list-item-avatar
                class="general-settings__currency-list primary--text"
              >
                {{ item.unicodeSymbol }}
              </v-list-item-avatar>
              <v-list-item-content>
                <v-list-item-title>
                  {{ item.name }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  {{
                    $t('general_settings.amount.labels.main_currency_subtitle')
                  }}
                </v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
          </template>
        </v-select>
      </settings-option>

      <numeric-separators-settings />

      <settings-option
        #default="{ error, success, update }"
        setting="currencyLocation"
        frontend-setting
        :error-message="
          $tc('general_settings.validation.currency_location.error')
        "
        :success-message="
          currencyLocation =>
            $tc('general_settings.validation.currency_location.success', 0, {
              currencyLocation
            })
        "
      >
        <v-radio-group
          v-model="currencyLocation"
          class="general-settings__fields__currency-location"
          :label="$t('general_settings.amount.label.currency_location')"
          row
          :success-messages="success"
          :error-messages="error"
          @change="update"
        >
          <v-radio
            :label="$t('general_settings.amount.label.location_before')"
            value="before"
          />
          <v-radio
            :label="$t('general_settings.amount.label.location_after')"
            value="after"
          />
        </v-radio-group>
      </settings-option>

      <div>
        <strong>
          {{ $t('general_settings.amount.label.resulting_format') }}
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
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import RoundingSettings from '@/components/settings/explorers/RoundingSettings.vue'; // eslint-disable-next-line @typescript-eslint/no-unused-vars
import FrontendSettings from '@/components/settings/FrontendSettings.vue';
import BalanceSaveFrequencySetting from '@/components/settings/general/BalanceSaveFrequencySetting.vue';
import DateDisplayFormatSetting from '@/components/settings/general/DateDisplayFormatSetting.vue';
import DateInputFormatSetting from '@/components/settings/general/DateInputFormatSetting.vue';
import FloatingPrecisionSetting from '@/components/settings/general/FloatingPrecisionSetting.vue';
import EthereumRpcNodeManager from '@/components/settings/general/rpc/EthereumRpcNodeManager.vue';
import RpcSettings from '@/components/settings/general/rpc/RpcSettings.vue';
import VersionUpdateFrequencySetting from '@/components/settings/general/VersionUpdateFrequencySetting.vue';
import PriceOracleSettings from '@/components/settings/PriceOracleSettings.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { setupGeneralSettings } from '@/composables/session';
import { useSettings } from '@/composables/settings';
import { currencies } from '@/data/currencies';
import { Currency } from '@/types/currency';
import { CurrencyLocation } from '@/types/currency-location';
import { bigNumberify } from '@/utils/bignumbers';

const { currency } = setupGeneralSettings();

const anonymousUsageAnalytics = ref<boolean>(false);

const currencyLocation = ref<CurrencyLocation>(CurrencyLocation.AFTER);
const selectedCurrency = ref<Currency>(currencies[0]);
const btcDerivationGapLimit = ref<string>('20');
const displayDateInLocaltime = ref<boolean>(true);
const treatEth2asEth = ref<boolean>(false);

const amountExample = bigNumberify(123456.789);

const { generalSettings, frontendSettings } = useSettings();

const loadFromState = () => {
  set(selectedCurrency, get(currency));
  const settings = get(generalSettings);
  set(anonymousUsageAnalytics, settings.submitUsageAnalytics);
  set(btcDerivationGapLimit, settings.btcDerivationGapLimit.toString());
  set(treatEth2asEth, settings.treatEth2AsEth);
  set(displayDateInLocaltime, settings.displayDateInLocaltime);

  const frontendSettingsVal = get(frontendSettings);
  set(currencyLocation, frontendSettingsVal.currencyLocation);
};

onMounted(() => {
  loadFromState();
});
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
