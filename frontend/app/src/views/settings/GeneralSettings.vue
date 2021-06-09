<template>
  <v-container class="general-settings">
    <v-row no-gutters>
      <v-col>
        <card>
          <template #title>
            {{ $t('general_settings.title') }}
          </template>

          <v-switch
            v-model="anonymousUsageAnalytics"
            class="general-settings__fields__anonymous-usage-statistics"
            color="primary"
            :label="$t('general_settings.labels.anonymous_analytics')"
            :success-messages="
              settingsMessages[ANONYMOUS_USAGE_ANALYTICS].success
            "
            :error-messages="settingsMessages[ANONYMOUS_USAGE_ANALYTICS].error"
            @change="onAnonymousUsageAnalyticsChange($event)"
          />

          <v-text-field
            v-model="balanceSaveFrequency"
            outlined
            class="general-settings__fields__balance-save-frequency"
            :label="$t('general_settings.labels.balance_saving_frequency')"
            type="number"
            :success-messages="settingsMessages[BALANCE_SAVE_FREQUENCY].success"
            :error-messages="settingsMessages[BALANCE_SAVE_FREQUENCY].error"
            @change="onBalanceSaveFrequencyChange($event)"
          />

          <v-text-field
            v-model="dateDisplayFormat"
            outlined
            class="general-settings__fields__date-display-format"
            :label="$t('general_settings.labels.date_display_format')"
            type="text"
            :rules="dateDisplayFormatRules"
            :success-messages="settingsMessages[DATE_DISPLAY_FORMAT].success"
            :error-messages="settingsMessages[DATE_DISPLAY_FORMAT].error"
            :hint="
              $t('general_settings.date_display_format_hint', {
                format: dateFormat
              })
            "
            persistent-hint
            @change="onDateDisplayFormatChange($event)"
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
                    @click="resetDateFormat()"
                    v-on="on"
                  >
                    <v-icon> mdi-backup-restore </v-icon>
                  </v-btn>
                </template>
                <span>{{ $t('general_settings.date_display_tooltip') }}</span>
              </v-tooltip>
            </template>
          </v-text-field>

          <v-switch
            v-model="displayDateInLocaltime"
            class="general-settings__fields__display-date-in-localtime"
            color="primary"
            :label="$t('general_settings.labels.display_date_in_localtime')"
            :success-messages="
              settingsMessages[DISPLAY_DATE_IN_LOCALTIME].success
            "
            :error-messages="settingsMessages[DISPLAY_DATE_IN_LOCALTIME].error"
            @change="onDisplayDateInLocaltimeChange($event)"
          />

          <v-text-field
            v-model="btcDerivationGapLimit"
            outlined
            class="general-settings__fields__btc-derivation-gap"
            :label="$t('general_settings.labels.btc_derivation_gap')"
            type="number"
            :success-messages="
              settingsMessages[BTC_DERIVATION_GAP_LIMIT].success
            "
            :error-messages="settingsMessages[BTC_DERIVATION_GAP_LIMIT].error"
            @change="onBtcDerivationGapLimitChanged($event)"
          />
          <date-format-help v-model="formatHelp" />
        </card>
        <card class="mt-8">
          <template #title>
            {{ $t('general_settings.amount.title') }}
          </template>
          <v-text-field
            v-model="floatingPrecision"
            outlined
            class="general-settings__fields__floating-precision"
            :label="$t('general_settings.amount.labels.floating_precision')"
            type="number"
            :success-messages="settingsMessages[FLOATING_PRECISION].success"
            :error-messages="settingsMessages[FLOATING_PRECISION].error"
            @change="onFloatingPrecisionChange($event)"
          />

          <v-select
            v-model="selectedCurrency"
            outlined
            class="general-settings__fields__currency-selector"
            :label="$t('general_settings.amount.labels.main_currency')"
            item-text="ticker_symbol"
            return-object
            :items="currencies"
            :success-messages="settingsMessages[SELECTED_CURRENCY].success"
            :error-messages="settingsMessages[SELECTED_CURRENCY].error"
            @change="onSelectedCurrencyChange($event)"
          >
            <template #item="{ item, attrs, on }">
              <v-list-item
                :id="`currency__${item.ticker_symbol.toLocaleLowerCase()}`"
                v-bind="attrs"
                v-on="on"
              >
                <v-list-item-avatar
                  class="general-settings__currency-list primary--text"
                >
                  {{ item.unicode_symbol }}
                </v-list-item-avatar>
                <v-list-item-content>
                  <v-list-item-title>
                    {{ item.name }}
                  </v-list-item-title>
                  <v-list-item-subtitle>
                    {{
                      $t(
                        'general_settings.amount.labels.main_currency_subtitle'
                      )
                    }}
                  </v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>
            </template>
          </v-select>

          <v-text-field
            v-model="thousandSeparator"
            outlined
            class="general-settings__fields__thousand-separator"
            :label="$t('general_settings.amount.label.thousand_separator')"
            type="text"
            :success-messages="settingsMessages[THOUSAND_SEPARATOR].success"
            :error-messages="settingsMessages[THOUSAND_SEPARATOR].error"
            @change="onThousandSeparatorChange($event)"
          />

          <v-text-field
            v-model="decimalSeparator"
            outlined
            class="general-settings__fields__decimal-separator"
            :label="$t('general_settings.amount.label.decimal_separator')"
            type="text"
            :success-messages="settingsMessages[DECIMAL_SEPARATOR].success"
            :error-messages="settingsMessages[DECIMAL_SEPARATOR].error"
            @change="onDecimalSeparatorChange($event)"
          />

          <v-radio-group
            v-model="currencyLocation"
            class="general-settings__fields__currency-location"
            :label="$t('general_settings.amount.label.currency_location')"
            row
            :success-messages="settingsMessages[CURRENCY_LOCATION].success"
            :error-messages="settingsMessages[CURRENCY_LOCATION].error"
            @change="onCurrencyLocationChange($event)"
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

          <strong>
            {{ $t('general_settings.amount.label.resulting_format') }}
          </strong>
          <amount-display :value="amountExample" show-currency="symbol" />

          <rounding-settings />
        </card>
        <card class="mt-8">
          <template #title>
            {{ $t('general_settings.local_nodes.title') }}
          </template>
          <v-text-field
            v-model="rpcEndpoint"
            outlined
            class="general-settings__fields__rpc-endpoint"
            :label="$t('general_settings.labels.rpc_endpoint')"
            type="text"
            :success-messages="settingsMessages[RPC_ENDPOINT].success"
            :error-messages="settingsMessages[RPC_ENDPOINT].error"
            clearable
            @paste="onRpcEndpointChange($event.clipboardData.getData('text'))"
            @click:clear="onRpcEndpointChange('')"
            @change="onRpcEndpointChange($event)"
          />

          <v-text-field
            v-model="ksmRpcEndpoint"
            outlined
            class="general-settings__fields__ksm-rpc-endpoint"
            :label="$t('general_settings.labels.ksm_rpc_endpoint')"
            type="text"
            :success-messages="settingsMessages[KSM_RPC_ENDPOINT].success"
            :error-messages="settingsMessages[KSM_RPC_ENDPOINT].error"
            clearable
            @paste="
              onKsmRpcEndpointChange($event.clipboardData.getData('text'))
            "
            @click:clear="onKsmRpcEndpointChange('')"
            @change="onKsmRpcEndpointChange($event)"
          />
        </card>
        <price-oracle-settings />
        <frontend-settings />
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import RoundingSettings from '@/components/settings/explorers/RoundingSettings.vue';
import FrontendSettings from '@/components/settings/FrontendSettings.vue';
import TimeFrameSettings from '@/components/settings/general/TimeFrameSettings.vue';
import PriceOracleSettings from '@/components/settings/PriceOracleSettings.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import {
  BaseMessage,
  makeMessage,
  settingsMessages
} from '@/components/settings/utils';
import { currencies } from '@/data/currencies';
import { displayDateFormatter } from '@/data/date_formatter';
import { Defaults } from '@/data/defaults';
import SettingsMixin from '@/mixins/settings-mixin';
import { Currency } from '@/model/currency';
import {
  CURRENCY_LOCATION,
  DECIMAL_SEPARATOR,
  THOUSAND_SEPARATOR
} from '@/store/settings/consts';
import { FrontendSettingsPayload } from '@/store/settings/types';
import { ActionStatus } from '@/store/types';
import {
  CURRENCY_AFTER,
  CurrencyLocation,
  SettingsUpdate
} from '@/typing/types';
import { bigNumberify } from '@/utils/bignumbers';
import DateFormatHelp from '@/views/settings/DateFormatHelp.vue';

const SETTING_FLOATING_PRECISION = 'floatingPrecision';
const SETTING_ANONYMOUS_USAGE_ANALYTICS = 'anonymousUsageAnalytics';
const SETTING_RPC_ENDPOINT = 'rpcEndpoint';
const SETTING_KSM_RPC_ENDPOINT = 'ksmRpcEndpoint';
const SETTING_BALANCE_SAVE_FREQUENCY = 'balanceSaveFrequency';
const SETTING_DATE_DISPLAY_FORMAT = 'dateDisplayFormat';
const SETTING_THOUSAND_SEPARATOR = 'thousandSeparator';
const SETTING_DECIMAL_SEPARATOR = 'decimalSeparator';
const SETTING_CURRENCY_LOCATION = 'currencyLocation';
const SETTING_SELECTED_CURRENCY = 'selectedCurrency';
const SETTING_BTC_DERIVATION_GAP_LIMIT = 'btcDerivationGapLimit';
const SETTING_DISPLAY_DATE_IN_LOCALTIME = 'displayDateInLocaltime';

const SETTINGS = [
  SETTING_FLOATING_PRECISION,
  SETTING_ANONYMOUS_USAGE_ANALYTICS,
  SETTING_RPC_ENDPOINT,
  SETTING_KSM_RPC_ENDPOINT,
  SETTING_BALANCE_SAVE_FREQUENCY,
  SETTING_DATE_DISPLAY_FORMAT,
  SETTING_THOUSAND_SEPARATOR,
  SETTING_DECIMAL_SEPARATOR,
  SETTING_CURRENCY_LOCATION,
  SETTING_SELECTED_CURRENCY,
  SETTING_BTC_DERIVATION_GAP_LIMIT,
  SETTING_DISPLAY_DATE_IN_LOCALTIME
] as const;

type SettingsEntries = typeof SETTINGS[number];

@Component({
  components: {
    DateFormatHelp,
    RoundingSettings,
    FrontendSettings,
    PriceOracleSettings,
    SettingCategory,
    TimeFrameSettings,
    AmountDisplay
  },
  computed: {
    ...mapGetters('session', ['currency'])
  }
})
export default class General extends Mixins<SettingsMixin<SettingsEntries>>(
  SettingsMixin
) {
  currency!: Currency;

  floatingPrecision: string = '0';
  anonymousUsageAnalytics: boolean = false;
  rpcEndpoint: string = Defaults.RPC_ENDPOINT;
  ksmRpcEndpoint: string = Defaults.KSM_RPC_ENDPOINT;
  balanceSaveFrequency: string = '0';
  dateDisplayFormat: string = '';
  thousandSeparator: string = '';
  decimalSeparator: string = '';
  currencyLocation: CurrencyLocation = CURRENCY_AFTER;
  selectedCurrency: Currency = currencies[0];
  btcDerivationGapLimit: string = '20';
  displayDateInLocaltime: boolean = true;

  formatHelp: boolean = false;
  readonly now = new Date();

  readonly FLOATING_PRECISION = SETTING_FLOATING_PRECISION;
  readonly ANONYMOUS_USAGE_ANALYTICS = SETTING_ANONYMOUS_USAGE_ANALYTICS;
  readonly RPC_ENDPOINT = SETTING_RPC_ENDPOINT;
  readonly KSM_RPC_ENDPOINT = SETTING_KSM_RPC_ENDPOINT;
  readonly BALANCE_SAVE_FREQUENCY = SETTING_BALANCE_SAVE_FREQUENCY;
  readonly DATE_DISPLAY_FORMAT = SETTING_DATE_DISPLAY_FORMAT;
  readonly THOUSAND_SEPARATOR = SETTING_THOUSAND_SEPARATOR;
  readonly DECIMAL_SEPARATOR = SETTING_DECIMAL_SEPARATOR;
  readonly CURRENCY_LOCATION = SETTING_CURRENCY_LOCATION;
  readonly SELECTED_CURRENCY = SETTING_SELECTED_CURRENCY;
  readonly BTC_DERIVATION_GAP_LIMIT = SETTING_BTC_DERIVATION_GAP_LIMIT;
  readonly DISPLAY_DATE_IN_LOCALTIME = SETTING_DISPLAY_DATE_IN_LOCALTIME;

  historicDateMenu: boolean = false;
  date: string = '';
  amountExample = bigNumberify(123456.789);

  get dateFormat(): string {
    return displayDateFormatter.format(this.now, this.dateDisplayFormat);
  }

  resetDateFormat() {
    this.dateDisplayFormat = Defaults.DEFAULT_DATE_DISPLAY_FORMAT;
    this.onDateDisplayFormatChange(this.dateDisplayFormat);
  }

  readonly dateDisplayFormatRules = [
    (v: string) => {
      if (!v) {
        return this.$t('general_settings.date_display.validation.empty');
      }
      if (!displayDateFormatter.containsValidDirectives(v)) {
        return this.$t(
          'general_settings.date_display.validation.invalid'
        ).toString();
      }
      return true;
    }
  ];

  async onBtcDerivationGapLimitChanged(limit: string) {
    const message = makeMessage(
      this.$t(
        'general_settings.validation.btc_derivation_gap.error'
      ).toString(),
      this.$t('general_settings.validation.btc_derivation_gap.success', {
        limit
      }).toString()
    );

    await this.update(
      { btc_derivation_gap_limit: parseInt(limit) },
      SETTING_BTC_DERIVATION_GAP_LIMIT,
      message
    );
  }

  async update(
    update: SettingsUpdate,
    setting: SettingsEntries,
    baseMessage: BaseMessage
  ): Promise<boolean> {
    const { message, success } = await this.settingsUpdate(update);

    this.validateSettingChange(
      setting,
      success ? 'success' : 'error',
      success ? baseMessage.success : `${baseMessage.error}: ${message}`
    );
    return success;
  }

  async onSelectedCurrencyChange(currency: Currency) {
    const symbol = currency.ticker_symbol;
    const message = makeMessage(
      `${this.$t('general_settings.validation.currency.error')}`,
      `${this.$t('general_settings.validation.currency.success', {
        symbol
      })}`
    );
    await this.update(
      { main_currency: symbol },
      SETTING_SELECTED_CURRENCY,
      message
    );
  }

  async modifyFrontendSetting(
    payload: FrontendSettingsPayload,
    setting: SettingsEntries,
    messages: BaseMessage
  ): Promise<ActionStatus> {
    const result = await this.updateSetting(payload);
    const { success } = result;

    this.validateSettingChange(
      setting,
      success ? 'success' : 'error',
      success ? messages.success : messages.error
    );
    return result;
  }

  async onThousandSeparatorChange(thousandSeparator: string) {
    const messages = makeMessage(
      this.$t(
        'general_settings.validation.thousand_separator.error'
      ).toString(),
      this.$t('general_settings.validation.thousand_separator.success', {
        thousandSeparator
      }).toString()
    );

    await this.modifyFrontendSetting(
      { [THOUSAND_SEPARATOR]: this.thousandSeparator },
      SETTING_THOUSAND_SEPARATOR,
      messages
    );
  }

  async onDecimalSeparatorChange(decimalSeparator: string) {
    const message = makeMessage(
      `${this.$t('general_settings.validation.decimal_separator.error')}`,
      this.$t('general_settings.validation.decimal_separator.success', {
        decimalSeparator
      }).toString()
    );

    await this.modifyFrontendSetting(
      { [DECIMAL_SEPARATOR]: this.decimalSeparator },
      SETTING_DECIMAL_SEPARATOR,
      message
    );
  }

  async onCurrencyLocationChange(currencyLocation: CurrencyLocation) {
    const message = makeMessage(
      `${this.$t('general_settings.validation.currency_location.error')}`,
      this.$t('general_settings.validation.currency_location.success', {
        currencyLocation
      }).toString()
    );

    await this.modifyFrontendSetting(
      { [CURRENCY_LOCATION]: this.currencyLocation },
      SETTING_CURRENCY_LOCATION,
      message
    );
  }

  async onFloatingPrecisionChange(precision: string) {
    const previousValue = this.generalSettings.floatingPrecision.toString();

    if (!this.notTheSame(precision, previousValue)) {
      return;
    }

    const params = {
      precision
    };
    const message = makeMessage(
      `${this.$t(
        'general_settings.validation.floating_precision.error',
        params
      )}`,
      `${this.$t(
        'general_settings.validation.floating_precision.success',
        params
      )}`
    );

    const success = await this.update(
      { ui_floating_precision: parseInt(precision) },
      SETTING_FLOATING_PRECISION,
      message
    );

    if (!success) {
      this.floatingPrecision = previousValue;
    }
  }

  async onAnonymousUsageAnalyticsChange(enabled: boolean) {
    const message = makeMessage(
      `${this.$t('general_settings.validation.analytics.error')}`
    );

    await this.update(
      { submit_usage_analytics: enabled },
      SETTING_ANONYMOUS_USAGE_ANALYTICS,
      message
    );
  }

  async onDisplayDateInLocaltimeChange(enabled: boolean) {
    const message = makeMessage(
      `${this.$t(
        'general_settings.validation.display_date_in_localtime.error'
      )}`
    );

    await this.update(
      { display_date_in_localtime: enabled },
      SETTING_DISPLAY_DATE_IN_LOCALTIME,
      message
    );
  }

  async onBalanceSaveFrequencyChange(frequency: string) {
    const previousValue = this.generalSettings.balanceSaveFrequency;

    if (!this.notTheSame(frequency, previousValue.toString())) {
      return;
    }

    const params = {
      frequency
    };
    const message = makeMessage(
      `${this.$t(
        'general_settings.validation.balance_frequency.error',
        params
      )}`,
      `${this.$t(
        'general_settings.validation.balance_frequency.success',
        params
      )}`
    );

    const success = await this.update(
      { balance_save_frequency: parseInt(frequency) },
      SETTING_BALANCE_SAVE_FREQUENCY,
      message
    );

    if (!success) {
      this.balanceSaveFrequency = previousValue.toString();
    }
  }

  async onDateDisplayFormatChange(dateFormat: string) {
    if (!displayDateFormatter.containsValidDirectives(dateFormat)) {
      return;
    }

    const message = makeMessage(
      `${this.$t('general_settings.validation.date_format.error')}`,
      `${this.$t('general_settings.validation.date_format.success', {
        dateFormat
      })}`
    );

    await this.update(
      { date_display_format: dateFormat },
      SETTING_DATE_DISPLAY_FORMAT,
      message
    );
  }

  async onRpcEndpointChange(endpoint: string) {
    const previousValue = this.generalSettings.ethRpcEndpoint;

    if (!this.notTheSame(endpoint, previousValue) && endpoint !== '') {
      return;
    }

    const message = makeMessage(
      `${this.$t('general_settings.validation.rpc.error')}`,
      endpoint
        ? `${this.$t('general_settings.validation.rpc.success_set', {
            endpoint
          })}`
        : `${this.$t('general_settings.validation.rpc.success_unset')}`
    );

    const success = await this.update(
      { eth_rpc_endpoint: endpoint },
      SETTING_RPC_ENDPOINT,
      message
    );

    if (!success) {
      this.rpcEndpoint = previousValue || '';
    }
  }

  async onKsmRpcEndpointChange(endpoint: string) {
    const previousValue = this.generalSettings.ksmRpcEndpoint;

    if (!this.notTheSame(endpoint, previousValue) && endpoint !== '') {
      return;
    }

    const message = makeMessage(
      this.$t('general_settings.validation.ksm_rpc.error').toString(),
      endpoint
        ? this.$t('general_settings.validation.ksm_rpc.success_set', {
            endpoint
          }).toString()
        : this.$t(
            'general_settings.validation.ksm_rpc.success_unset'
          ).toString()
    );

    const success = await this.update(
      { ksm_rpc_endpoint: endpoint },
      SETTING_KSM_RPC_ENDPOINT,
      message
    );

    if (!success) {
      this.ksmRpcEndpoint = previousValue || '';
    }
  }

  formatDate(date: string) {
    if (!date) return '';

    const [year, month, day] = date.split('-');
    return `${day}/${month}/${year}`;
  }

  parseDate(date: string) {
    if (
      !/^([0-2]\d|[3][0-1])\/([0]\d|[1][0-2])\/([2][01]|[1][6-9])\d{2}$/.test(
        date
      )
    )
      return null;

    const [day, month, year] = date.split('/');
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }

  get currencies(): Currency[] {
    return currencies;
  }

  created() {
    this.settingsMessages = settingsMessages(SETTINGS);
  }

  mounted() {
    this.loadFromState();
  }

  private loadFromState() {
    this.selectedCurrency = this.currency;
    const settings = this.generalSettings;
    this.floatingPrecision = settings.floatingPrecision.toString();
    this.anonymousUsageAnalytics = settings.anonymousUsageAnalytics;
    this.rpcEndpoint = settings.ethRpcEndpoint;
    this.ksmRpcEndpoint = settings.ksmRpcEndpoint;
    this.balanceSaveFrequency = settings.balanceSaveFrequency.toString();
    this.dateDisplayFormat = settings.dateDisplayFormat;
    this.btcDerivationGapLimit = settings.btcDerivationGapLimit.toString();
    const state = this.$store.state;
    this.thousandSeparator = state.settings![THOUSAND_SEPARATOR];
    this.decimalSeparator = state.settings![DECIMAL_SEPARATOR];
    this.currencyLocation = state.settings![CURRENCY_LOCATION];
  }

  notTheSame<T>(value: T, oldValue: T): T | undefined {
    return value !== oldValue ? value : undefined;
  }
}
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
