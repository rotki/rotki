<template>
  <div class="general-settings mt-n8">
    <date-format-help v-model="formatHelp" />
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

      <v-row>
        <v-col class="grow">
          <settings-option
            #default="{ error, success, update }"
            setting="versionUpdateCheckFrequency"
            frontend-setting
            :transform="value => (value ? parseInt(value) : value)"
            :rules="versionUpdateCheckFrequencyRules"
            :error-message="
              $t(
                'general_settings.validation.version_update_check_frequency.error'
              )
            "
            @finished="resetVersionUpdateCheckFrequency"
          >
            <v-text-field
              v-model="versionUpdateCheckFrequency"
              outlined
              :disabled="!versionUpdateCheckEnabled"
              type="number"
              :rules="versionUpdateCheckFrequencyRules"
              min="1"
              :max="maxVersionUpdateCheckFrequency"
              :label="$t('general_settings.labels.version_update_check')"
              persistent-hint
              :hint="$t('general_settings.version_update_check_hint')"
              :success-messages="success"
              :error-messages="error"
              @change="update"
            />
          </settings-option>
        </v-col>
        <v-col class="shrink">
          <settings-option
            #default="{ update }"
            setting="versionUpdateCheckFrequency"
            frontend-setting
            :transform="value => (value ? 24 : -1)"
            @finished="resetVersionUpdateCheckFrequency"
          >
            <v-switch
              v-model="versionUpdateCheckEnabled"
              class="mt-3"
              :label="
                $t('general_settings.labels.version_update_check_enabled')
              "
              @change="update"
            />
          </settings-option>
        </v-col>
      </v-row>

      <settings-option
        #default="{ error, success, update }"
        setting="balanceSaveFrequency"
        :rules="balanceSaveFrequencyRules"
        :transform="value => (value ? parseInt(value) : value)"
        :error-message="
          $tc('general_settings.validation.balance_frequency.error')
        "
        :success-message="
          frequency =>
            $tc('general_settings.validation.balance_frequency.success', 0, {
              frequency
            })
        "
        @finished="resetBalanceSaveFrequency"
      >
        <v-text-field
          v-model="balanceSaveFrequency"
          outlined
          min="1"
          :max="maxBalanceSaveFrequency"
          :rules="balanceSaveFrequencyRules"
          class="mt-2 general-settings__fields__balance-save-frequency"
          :label="$t('general_settings.labels.balance_saving_frequency')"
          type="number"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="dateDisplayFormat"
        :rules="dateFormatRules"
        :error-message="
          $tc('general_settings.validation.date_display_format.error')
        "
        :success-message="
          dateFormat =>
            $tc('general_settings.validation.date_display_format.success', 0, {
              dateFormat
            })
        "
        @finished="resetDateDisplayFormat"
      >
        <v-text-field
          v-model="dateDisplayFormat"
          outlined
          class="general-settings__fields__date-display-format"
          :label="$t('general_settings.labels.date_display_format')"
          type="text"
          :rules="dateFormatRules"
          :success-messages="success"
          :error-messages="error"
          :hint="
            $t('general_settings.date_display_format_hint', {
              format: dateDisplayFormatExample
            })
          "
          persistent-hint
          @change="update"
        >
          <template #append>
            <v-btn small icon @click="formatHelp = true">
              <v-icon small> mdi-information </v-icon>
            </v-btn>
          </template>
          <template #append-outer>
            <v-tooltip top open-delay="400">
              <template #activator="{ on, attrs }">
                <v-btn
                  class="general-settings__date-restore"
                  icon
                  v-bind="attrs"
                  @click="update(defaultDateDisplayFormat)"
                  v-on="on"
                >
                  <v-icon> mdi-backup-restore </v-icon>
                </v-btn>
              </template>
              <span>{{ $t('general_settings.date_display_tooltip') }}</span>
            </v-tooltip>
          </template>
        </v-text-field>
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="dateInputFormat"
        frontend-setting
        :rules="dateFormatRules"
        :error-message="
          $tc('general_settings.validation.date_input_format.error')
        "
        :success-message="
          dateFormat =>
            $tc('general_settings.validation.date_input_format.success', 0, {
              dateFormat
            })
        "
        @finished="resetDateInputFormat"
      >
        <date-input-format-selector
          v-model="dateInputFormat"
          :label="$t('general_settings.labels.date_input_format')"
          class="pt-4 general-settings__fields__date-input-format"
          :rules="dateFormatRules"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>

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

      <settings-option
        #default="{ error, success, update }"
        setting="uiFloatingPrecision"
        :rules="floatingPrecisionRules"
        :transform="value => (value ? parseInt(value) : value)"
        :error-message="
          precision =>
            $tc('general_settings.validation.floating_precision.error', 0, {
              precision
            })
        "
        :success-message="
          precision =>
            $tc('general_settings.validation.floating_precision.success', 0, {
              precision
            })
        "
        @finished="resetFloatingPrecision"
      >
        <v-text-field
          v-model="floatingPrecision"
          outlined
          min="1"
          :max="maxFloatingPrecision"
          :rules="floatingPrecisionRules"
          class="general-settings__fields__floating-precision"
          :label="$t('general_settings.amount.labels.floating_precision')"
          type="number"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>

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

      <settings-option
        #default="{ error, success, update }"
        setting="thousandSeparator"
        frontend-setting
        :rules="thousandSeparatorRules"
        :error-message="
          $tc('general_settings.validation.thousand_separator.error')
        "
        :success-message="
          thousandSeparator =>
            $tc('general_settings.validation.thousand_separator.success', 0, {
              thousandSeparator
            })
        "
      >
        <v-text-field
          v-model="thousandSeparator"
          outlined
          maxlength="1"
          class="general-settings__fields__thousand-separator"
          :label="$t('general_settings.amount.label.thousand_separator')"
          type="text"
          :rules="thousandSeparatorRules"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="decimalSeparator"
        frontend-setting
        :rules="decimalSeparatorRules"
        :error-message="
          $tc('general_settings.validation.decimal_separator.error')
        "
        :success-message="
          decimalSeparator =>
            $tc('general_settings.validation.decimal_separator.success', 0, {
              decimalSeparator
            })
        "
      >
        <v-text-field
          v-model="decimalSeparator"
          outlined
          maxlength="1"
          class="general-settings__fields__decimal-separator"
          :label="$t('general_settings.amount.label.decimal_separator')"
          type="text"
          :rules="decimalSeparatorRules"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>

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
import { computed, onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import RoundingSettings from '@/components/settings/explorers/RoundingSettings.vue';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import FrontendSettings from '@/components/settings/FrontendSettings.vue';
import DateInputFormatSelector from '@/components/settings/general/DateInputFormatSelector.vue';
import EthereumRpcNodeManager from '@/components/settings/general/rpc/EthereumRpcNodeManager.vue';
import RpcSettings from '@/components/settings/general/rpc/RpcSettings.vue';
import PriceOracleSettings from '@/components/settings/PriceOracleSettings.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { setupGeneralSettings } from '@/composables/session';
import { useSettings } from '@/composables/settings';
import { Constraints } from '@/data/constraints';
import { currencies } from '@/data/currencies';
import { displayDateFormatter } from '@/data/date_formatter';
import { Defaults } from '@/data/defaults';
import i18n from '@/i18n';
import { Currency } from '@/types/currency';
import { CurrencyLocation } from '@/types/currency-location';
import { bigNumberify } from '@/utils/bignumbers';
import DateFormatHelp from '@/views/settings/DateFormatHelp.vue';

const { currency } = setupGeneralSettings();

const floatingPrecision = ref<string>('0');
const anonymousUsageAnalytics = ref<boolean>(false);
const balanceSaveFrequency = ref<string>('0');
const dateDisplayFormat = ref<string>('');
const dateInputFormat = ref<string>('');
const thousandSeparator = ref<string>('');
const decimalSeparator = ref<string>('');
const currencyLocation = ref<CurrencyLocation>(CurrencyLocation.AFTER);
const selectedCurrency = ref<Currency>(currencies[0]);
const btcDerivationGapLimit = ref<string>('20');
const displayDateInLocaltime = ref<boolean>(true);
const versionUpdateCheckFrequency = ref<string>('');
const versionUpdateCheckEnabled = ref<boolean>(false);
const treatEth2asEth = ref<boolean>(false);

const formatHelp = ref<boolean>(false);

const now = new Date();

const amountExample = bigNumberify(123456.789);

const dateDisplayFormatExample = computed<string>(() => {
  return displayDateFormatter.format(now, get(dateDisplayFormat));
});

const defaultDateDisplayFormat = Defaults.DEFAULT_DATE_DISPLAY_FORMAT;
const dateFormatRules = [
  (v: string) => {
    if (!v) {
      return i18n
        .t('general_settings.date_display.validation.empty')
        .toString();
    }
    if (!displayDateFormatter.containsValidDirectives(v)) {
      return i18n
        .t('general_settings.date_display.validation.invalid')
        .toString();
    }
    return true;
  }
];

const maxVersionUpdateCheckFrequency = Constraints.MAX_HOURS_DELAY;
const versionUpdateCheckFrequencyRules = [
  (v: string) =>
    !!v ||
    !get(versionUpdateCheckEnabled) ||
    i18n
      .t('general_settings.validation.version_update_check_frequency.non_empty')
      .toString(),
  (v: string) =>
    (v && parseInt(v) > 0 && parseInt(v) < maxVersionUpdateCheckFrequency) ||
    !get(versionUpdateCheckEnabled) ||
    i18n
      .t(
        'general_settings.validation.version_update_check_frequency.invalid_frequency',
        0,
        {
          start: 1,
          end: maxVersionUpdateCheckFrequency
        }
      )
      .toString()
];

const thousandSeparatorRules = computed<((v: string) => boolean | string)[]>(
  () => {
    return [
      (v: string) => {
        if (!v) {
          return i18n
            .t('general_settings.thousand_separator.validation.empty')
            .toString();
        }
        if (v === get(decimalSeparator)) {
          return i18n
            .t(
              'general_settings.thousand_separator.validation.cannot_be_the_same'
            )
            .toString();
        }
        if (/[0-9]/.test(v)) {
          return i18n
            .t(
              'general_settings.thousand_separator.validation.cannot_be_numeric_character'
            )
            .toString();
        }
        return true;
      }
    ];
  }
);

const decimalSeparatorRules = computed<((v: string) => boolean | string)[]>(
  () => {
    return [
      (v: string) => {
        if (!v) {
          return i18n
            .t('general_settings.decimal_separator.validation.empty')
            .toString();
        }
        if (v === get(thousandSeparator)) {
          return i18n
            .t(
              'general_settings.decimal_separator.validation.cannot_be_the_same'
            )
            .toString();
        }
        if (/[0-9]/.test(v)) {
          return i18n
            .t(
              'general_settings.decimal_separator.validation.cannot_be_numeric_character'
            )
            .toString();
        }
        return true;
      }
    ];
  }
);

const maxFloatingPrecision = 8;
const floatingPrecisionRules = [
  (v: string) =>
    !!v ||
    i18n
      .t('general_settings.validation.floating_precision.non_empty')
      .toString()
];

const maxBalanceSaveFrequency = Constraints.MAX_HOURS_DELAY;
const balanceSaveFrequencyRules = [
  (v: string) =>
    !!v ||
    i18n
      .t('general_settings.validation.balance_frequency.non_empty')
      .toString(),
  (v: string) =>
    (v && parseInt(v) > 0 && parseInt(v) < maxBalanceSaveFrequency) ||
    i18n
      .t('general_settings.validation.balance_frequency.invalid_frequency', {
        start: 1,
        end: maxBalanceSaveFrequency
      })
      .toString()
];

const { generalSettings, frontendSettings } = useSettings();

const resetBalanceSaveFrequency = () => {
  const settings = get(generalSettings);
  set(balanceSaveFrequency, settings.balanceSaveFrequency.toString());
};

const resetFloatingPrecision = () => {
  const settings = get(generalSettings);
  set(floatingPrecision, settings.uiFloatingPrecision.toString());
};

const resetDateDisplayFormat = () => {
  const settings = get(generalSettings);
  set(dateDisplayFormat, settings.dateDisplayFormat);
};

const resetVersionUpdateCheckFrequency = () => {
  const frontendSettingsVal = get(frontendSettings);
  const frequency = frontendSettingsVal.versionUpdateCheckFrequency;
  set(versionUpdateCheckEnabled, frequency > 0);
  set(
    versionUpdateCheckFrequency,
    get(versionUpdateCheckEnabled) ? frequency.toString() : ''
  );
};

const resetDateInputFormat = () => {
  const frontendSettingsVal = get(frontendSettings);
  set(dateInputFormat, frontendSettingsVal.dateInputFormat);
};

const loadFromState = () => {
  set(selectedCurrency, get(currency));
  const settings = get(generalSettings);
  set(anonymousUsageAnalytics, settings.submitUsageAnalytics);
  set(btcDerivationGapLimit, settings.btcDerivationGapLimit.toString());
  set(treatEth2asEth, settings.treatEth2AsEth);
  set(displayDateInLocaltime, settings.displayDateInLocaltime);
  resetBalanceSaveFrequency();
  resetFloatingPrecision();
  resetDateDisplayFormat();

  const frontendSettingsVal = get(frontendSettings);
  set(thousandSeparator, frontendSettingsVal.thousandSeparator);
  set(decimalSeparator, frontendSettingsVal.decimalSeparator);
  set(currencyLocation, frontendSettingsVal.currencyLocation);
  resetVersionUpdateCheckFrequency();
  resetDateInputFormat();
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
