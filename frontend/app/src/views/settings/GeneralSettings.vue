<template>
  <v-container class="general-settings">
    <v-row no-gutters>
      <v-col>
        <v-card>
          <v-card-title>{{ $t('general_settings.title') }}</v-card-title>
          <v-card-text>
            <v-switch
              v-model="anonymizedLogs"
              class="general-settings__fields__anonymized-logs"
              :label="$t('general_settings.labels.anonymized_logs')"
              color="primary"
              :success-messages="settingsMessages[ANONYMIZED_LOGS].success"
              :error-messages="settingsMessages[ANONYMIZED_LOGS].error"
              @change="onAnonymizedLogsChange($event)"
            />
            <v-switch
              v-model="anonymousUsageAnalytics"
              class="general-settings__fields__anonymous-usage-statistics"
              color="primary"
              :label="$t('general_settings.labels.anonymous_analytics')"
              :success-messages="
                settingsMessages[ANONYMOUS_USAGE_ANALYTICS].success
              "
              :error-messages="
                settingsMessages[ANONYMOUS_USAGE_ANALYTICS].error
              "
              @change="onAnonymousUsageAnalyticsChange($event)"
            />

            <v-text-field
              v-model="balanceSaveFrequency"
              class="general-settings__fields__balance-save-frequency"
              :label="$t('general_settings.labels.balance_saving_frequency')"
              type="number"
              :success-messages="
                settingsMessages[BALANCE_SAVE_FREQUENCY].success
              "
              :error-messages="settingsMessages[BALANCE_SAVE_FREQUENCY].error"
              @change="onBalanceSaveFrequencyChange($event)"
            />

            <v-text-field
              v-model="dateDisplayFormat"
              class="general-settings__fields__date-display-format"
              :label="$t('general_settings.labels.date_display_format')"
              type="text"
              :success-messages="settingsMessages[DATE_DISPLAY_FORMAT].success"
              :error-messages="settingsMessages[DATE_DISPLAY_FORMAT].error"
              @change="onDateDisplayFormatChange($event)"
            />

            <v-text-field
              v-model="btcDerivationGapLimit"
              class="general-settings__fields__btc-derivation-gap"
              :label="$t('general_settings.labels.btc_derivation_gap')"
              type="number"
              :success-messages="
                settingsMessages[BTC_DERIVATION_GAP_LIMIT].success
              "
              :error-messages="settingsMessages[BTC_DERIVATION_GAP_LIMIT].error"
              @change="onBtcDerivationGapLimitChanged($event)"
            />
          </v-card-text>
        </v-card>
        <v-card class="mt-5">
          <v-card-title>
            {{ $t('general_settings.amount.title') }}
          </v-card-title>
          <v-card-text>
            <v-text-field
              v-model="floatingPrecision"
              class="general-settings__fields__floating-precision"
              :label="$t('general_settings.amount.labels.floating_precision')"
              type="number"
              :success-messages="settingsMessages[FLOATING_PRECISION].success"
              :error-messages="settingsMessages[FLOATING_PRECISION].error"
              @change="onFloatingPrecisionChange($event)"
            />

            <v-select
              v-model="selectedCurrency"
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
              class="general-settings__fields__thousand-separator"
              :label="$t('general_settings.amount.label.thousand_separator')"
              type="text"
              :success-messages="settingsMessages[THOUSAND_SEPARATOR].success"
              :error-messages="settingsMessages[THOUSAND_SEPARATOR].error"
              @change="onThousandSeparatorChange($event)"
            />

            <v-text-field
              v-model="decimalSeparator"
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
          </v-card-text>
        </v-card>
        <v-card class="mt-5">
          <v-card-title>
            {{ $t('general_settings.local_nodes.title') }}
          </v-card-title>
          <v-card-text>
            <v-text-field
              v-model="rpcEndpoint"
              class="general-settings__fields__rpc-endpoint"
              :label="$t('general_settings.labels.rpc_endpoint')"
              type="text"
              data-vv-name="eth_rpc_endpoint"
              :success-messages="settingsMessages[RPC_ENDPOINT].success"
              :error-messages="settingsMessages[RPC_ENDPOINT].error"
              clearable
              @paste="onRpcEndpointChange($event.clipboardData.getData('text'))"
              @click:clear="onRpcEndpointChange('')"
              @change="onRpcEndpointChange($event)"
            />

            <v-text-field
              v-model="ksmRpcEndpoint"
              class="general-settings__fields__ksm-rpc-endpoint"
              :label="$t('general_settings.labels.ksm_rpc_endpoint')"
              type="text"
              data-vv-name="eth_rpc_endpoint"
              :success-messages="settingsMessages[KSM_RPC_ENDPOINT].success"
              :error-messages="settingsMessages[KSM_RPC_ENDPOINT].error"
              clearable
              @paste="
                onKsmRpcEndpointChange($event.clipboardData.getData('text'))
              "
              @click:clear="onKsmRpcEndpointChange('')"
              @change="onKsmRpcEndpointChange($event)"
            />
          </v-card-text>
        </v-card>
        <v-card class="mt-5">
          <v-card-title>
            {{ $t('general_settings.frontend.title') }}
          </v-card-title>
          <v-card-text>
            <v-switch
              v-model="scrambleData"
              class="general-settings__fields__scramble-data"
              :label="$t('general_settings.frontend.label.scramble')"
              :success-messages="settingsMessages[SCRAMBLE_DATA].success"
              :error-messages="settingsMessages[SCRAMBLE_DATA].error"
              @change="onScrambleDataChange($event)"
            />
            <time-frame-settings
              :message="settingsMessages[TIMEFRAME]"
              :value="defaultGraphTimeframe"
              @timeframe-change="onTimeframeChange"
            />
            <v-text-field
              v-model="queryPeriod"
              class="general-settings__fields__periodic-client-query-period"
              :label="$t('general_settings.frontend.label.query_period')"
              :hint="$t('general_settings.frontend.label.query_period_hint')"
              type="number"
              min="5"
              max="3600"
              :success-messages="settingsMessages[QUERY_PERIOD].success"
              :error-messages="settingsMessages[QUERY_PERIOD].error"
              @change="onQueryPeriodChange($event)"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import TimeFrameSettings from '@/components/settings/general/TimeFrameSettings.vue';
import { currencies } from '@/data/currencies';
import { Defaults } from '@/data/defaults';
import { Currency } from '@/model/currency';
import { monitor } from '@/services/monitoring';
import {
  CURRENCY_LOCATION,
  DECIMAL_SEPARATOR,
  QUERY_PERIOD,
  THOUSAND_SEPARATOR,
  TIMEFRAME_ALL,
  TIMEFRAME_SETTING
} from '@/store/settings/consts';
import {
  FrontendSettingsPayload,
  TimeFrameSetting
} from '@/store/settings/types';
import { ActionStatus } from '@/store/types';
import {
  CURRENCY_AFTER,
  CurrencyLocation,
  GeneralSettings,
  SettingsUpdate
} from '@/typing/types';
import { bigNumberify } from '@/utils/bignumbers';
import Settings from '@/views/settings/Settings.vue';

type BaseMessage = { success: string; error: string };

const message: () => BaseMessage = () => ({ success: '', error: '' });

const SETTING_FLOATING_PRECISION = 'floatingPrecision';
const SETTING_ANONYMIZED_LOGS = 'anonymizedLogs';
const SETTING_ANONYMOUS_USAGE_ANALYTICS = 'anonymousUsageAnalytics';
const SETTING_RPC_ENDPOINT = 'rpcEndpoint';
const SETTING_KSM_RPC_ENDPOINT = 'ksmRpcEndpoint';
const SETTING_BALANCE_SAVE_FREQUENCY = 'balanceSaveFrequency';
const SETTING_DATE_DISPLAY_FORMAT = 'dateDisplayFormat';
const SETTING_THOUSAND_SEPARATOR = 'thousandSeparator';
const SETTING_DECIMAL_SEPARATOR = 'decimalSeparator';
const SETTING_CURRENCY_LOCATION = 'currencyLocation';
const SETTING_SELECTED_CURRENCY = 'selectedCurrency';
const SETTING_SCRAMBLE_DATA = 'scrambleData';
const SETTING_TIMEFRAME = 'timeframe';
const SETTING_QUERY_PERIOD = 'queryPeriod';
const SETTING_BTC_DERIVATION_GAP_LIMIT = 'btcDerivationGapLimit';

const SETTINGS = [
  SETTING_FLOATING_PRECISION,
  SETTING_ANONYMIZED_LOGS,
  SETTING_ANONYMOUS_USAGE_ANALYTICS,
  SETTING_RPC_ENDPOINT,
  SETTING_KSM_RPC_ENDPOINT,
  SETTING_BALANCE_SAVE_FREQUENCY,
  SETTING_DATE_DISPLAY_FORMAT,
  SETTING_THOUSAND_SEPARATOR,
  SETTING_DECIMAL_SEPARATOR,
  SETTING_CURRENCY_LOCATION,
  SETTING_SELECTED_CURRENCY,
  SETTING_SCRAMBLE_DATA,
  SETTING_TIMEFRAME,
  SETTING_QUERY_PERIOD,
  SETTING_BTC_DERIVATION_GAP_LIMIT
] as const;

type SettingsEntries = typeof SETTINGS[number];
type GeneralSettingsMessages = { [setting in SettingsEntries]: BaseMessage };

const settingsMessages: () => GeneralSettingsMessages = () => {
  const settings: GeneralSettingsMessages = {} as GeneralSettingsMessages;
  for (const setting of SETTINGS) {
    settings[setting] = message();
  }
  return settings;
};

@Component({
  components: {
    TimeFrameSettings,
    AmountDisplay
  },
  computed: {
    ...mapState('session', ['generalSettings']),
    ...mapGetters('session', ['currency'])
  },
  methods: {
    ...mapActions('session', ['settingsUpdate']),
    ...mapActions('settings', ['updateSetting'])
  }
})
export default class General extends Settings {
  generalSettings!: GeneralSettings;
  currency!: Currency;

  floatingPrecision: string = '0';
  anonymizedLogs: boolean = false;
  anonymousUsageAnalytics: boolean = false;
  rpcEndpoint: string = Defaults.RPC_ENDPOINT;
  ksmRpcEndpoint: string = Defaults.KSM_RPC_ENDPOINT;
  balanceSaveFrequency: string = '0';
  dateDisplayFormat: string = '';
  thousandSeparator: string = '';
  decimalSeparator: string = '';
  currencyLocation: CurrencyLocation = CURRENCY_AFTER;
  selectedCurrency: Currency = currencies[0];
  scrambleData: boolean = false;
  defaultGraphTimeframe: TimeFrameSetting = TIMEFRAME_ALL;
  settingsUpdate!: (update: SettingsUpdate) => Promise<ActionStatus>;
  updateSetting!: (payload: FrontendSettingsPayload) => Promise<ActionStatus>;
  queryPeriod: string = '5';
  btcDerivationGapLimit: string = '20';

  readonly settingsMessages: GeneralSettingsMessages = settingsMessages();
  readonly FLOATING_PRECISION = SETTING_FLOATING_PRECISION;
  readonly ANONYMIZED_LOGS = SETTING_ANONYMIZED_LOGS;
  readonly ANONYMOUS_USAGE_ANALYTICS = SETTING_ANONYMOUS_USAGE_ANALYTICS;
  readonly RPC_ENDPOINT = SETTING_RPC_ENDPOINT;
  readonly KSM_RPC_ENDPOINT = SETTING_KSM_RPC_ENDPOINT;
  readonly BALANCE_SAVE_FREQUENCY = SETTING_BALANCE_SAVE_FREQUENCY;
  readonly DATE_DISPLAY_FORMAT = SETTING_DATE_DISPLAY_FORMAT;
  readonly THOUSAND_SEPARATOR = SETTING_THOUSAND_SEPARATOR;
  readonly DECIMAL_SEPARATOR = SETTING_DECIMAL_SEPARATOR;
  readonly CURRENCY_LOCATION = SETTING_CURRENCY_LOCATION;
  readonly SELECTED_CURRENCY = SETTING_SELECTED_CURRENCY;
  readonly SCRAMBLE_DATA = SETTING_SCRAMBLE_DATA;
  readonly TIMEFRAME = SETTING_TIMEFRAME;
  readonly QUERY_PERIOD = SETTING_QUERY_PERIOD;
  readonly BTC_DERIVATION_GAP_LIMIT = SETTING_BTC_DERIVATION_GAP_LIMIT;

  historicDateMenu: boolean = false;
  date: string = '';
  amountExample = bigNumberify(123456.789);

  async onBtcDerivationGapLimitChanged(limit: string) {
    const message: BaseMessage = {
      success: this.$t(
        'general_settings.validation.btc_derivation_gap.success',
        { limit }
      ).toString(),
      error: this.$t(
        'general_settings.validation.btc_derivation_gap.error'
      ).toString()
    };

    await this.update(
      { btc_derivation_gap_limit: parseInt(limit) },
      SETTING_BTC_DERIVATION_GAP_LIMIT,
      message
    );
  }

  async onTimeframeChange(timeframe: TimeFrameSetting) {
    const payload: FrontendSettingsPayload = {
      [TIMEFRAME_SETTING]: timeframe
    };

    const messages: BaseMessage = {
      success: this.$t('general_settings.validation.timeframe.success', {
        timeframe: timeframe
      }).toString(),
      error: this.$t('general_settings.validation.timeframe.error').toString()
    };

    const { success } = await this.modifyFrontendSetting(
      payload,
      SETTING_TIMEFRAME,
      messages
    );

    if (success) {
      this.defaultGraphTimeframe = timeframe;
    }
  }

  async update(
    update: SettingsUpdate,
    setting: string,
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

  onScrambleDataChange(enabled: boolean) {
    const { commit } = this.$store;
    const previousValue = this.$store.state.session.scrambleData;

    let success: boolean = false;
    let message: string | undefined;

    try {
      commit('session/scrambleData', enabled);
      success = true;
    } catch (error) {
      this.scrambleData = previousValue;
      message = error.message;
    }

    this.validateSettingChange(
      SETTING_SCRAMBLE_DATA,
      success ? 'success' : 'error',
      success
        ? ''
        : `${this.$t('general_settings.validation.scramble.error', {
            message
          })}`
    );
  }

  async onQueryPeriodChange(queryPeriod: string) {
    const period = parseInt(queryPeriod);
    if (period < 5 || period > 3600) {
      const message = `${this.$t(
        'general_settings.validation.periodic_query.invalid_period',
        {
          start: 5,
          end: 3600
        }
      )}`;
      this.validateSettingChange(
        SETTING_QUERY_PERIOD,
        'error',
        `${this.$t('general_settings.validation.periodic_query.error', {
          message
        })}`
      );
      this.queryPeriod = this.$store.state.settings![QUERY_PERIOD].toString();
      return;
    }

    const messages: BaseMessage = {
      success: this.$t('general_settings.validation.periodic_query.success', {
        period
      }).toString(),
      error: this.$t(
        'general_settings.validation.periodic_query.error'
      ).toString()
    };

    const { success } = await this.modifyFrontendSetting(
      {
        [QUERY_PERIOD]: period
      },
      SETTING_QUERY_PERIOD,
      messages
    );

    if (success) {
      monitor.stop();
      monitor.start();
    }
  }

  async onSelectedCurrencyChange(currency: Currency) {
    const symbol = currency.ticker_symbol;
    const message: BaseMessage = {
      success: `${this.$t('general_settings.validation.currency.success', {
        symbol
      })}`,
      error: `${this.$t('general_settings.validation.currency.error')}`
    };
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
    const messages: BaseMessage = {
      success: this.$t(
        'general_settings.validation.thousand_separator.success',
        { thousandSeparator }
      ).toString(),
      error: this.$t(
        'general_settings.validation.thousand_separator.error'
      ).toString()
    };

    await this.modifyFrontendSetting(
      { [THOUSAND_SEPARATOR]: this.thousandSeparator },
      SETTING_THOUSAND_SEPARATOR,
      messages
    );
  }

  async onDecimalSeparatorChange(decimalSeparator: string) {
    const message: BaseMessage = {
      success: this.$t(
        'general_settings.validation.decimal_separator.success',
        { decimalSeparator }
      ).toString(),
      error: `${this.$t('general_settings.validation.decimal_separator.error')}`
    };

    await this.modifyFrontendSetting(
      { [DECIMAL_SEPARATOR]: this.decimalSeparator },
      SETTING_DECIMAL_SEPARATOR,
      message
    );
  }

  async onCurrencyLocationChange(currencyLocation: CurrencyLocation) {
    const message: BaseMessage = {
      success: this.$t(
        'general_settings.validation.currency_location.success',
        { currencyLocation }
      ).toString(),
      error: `${this.$t('general_settings.validation.currency_location.error')}`
    };

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
    const message: BaseMessage = {
      success: `${this.$t(
        'general_settings.validation.floating_precision.success',
        params
      )}`,
      error: `${this.$t(
        'general_settings.validation.floating_precision.error',
        params
      )}`
    };

    const success = await this.update(
      { ui_floating_precision: parseInt(precision) },
      SETTING_FLOATING_PRECISION,
      message
    );

    if (!success) {
      this.floatingPrecision = previousValue;
    }
  }

  async onAnonymizedLogsChange(enabled: boolean) {
    const message: BaseMessage = {
      success: '',
      error: `${this.$t('general_settings.validation.anonymized_logs.error')}`
    };

    await this.update({ anonymized_logs: enabled }, 'anonymizedLogs', message);
  }

  async onAnonymousUsageAnalyticsChange(enabled: boolean) {
    const message: BaseMessage = {
      success: '',
      error: `${this.$t('general_settings.validation.analytics.error')}`
    };

    await this.update(
      { submit_usage_analytics: enabled },
      SETTING_ANONYMOUS_USAGE_ANALYTICS,
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
    const message: BaseMessage = {
      success: `${this.$t(
        'general_settings.validation.balance_frequency.success',
        params
      )}`,
      error: `${this.$t(
        'general_settings.validation.balance_frequency.error',
        params
      )}`
    };

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
    const message: BaseMessage = {
      success: `${this.$t('general_settings.validation.date_format.success', {
        dateFormat
      })}`,
      error: `${this.$t('general_settings.validation.date_format.error')}`
    };

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

    const message: BaseMessage = {
      success: endpoint
        ? `${this.$t('general_settings.validation.rpc.success_set', {
            endpoint
          })}`
        : `${this.$t('general_settings.validation.rpc.success_unset')}`,
      error: `${this.$t('general_settings.validation.rpc.error')}`
    };

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

    const message: BaseMessage = {
      success: endpoint
        ? this.$t('general_settings.validation.ksm_rpc.success_set', {
            endpoint
          }).toString()
        : this.$t(
            'general_settings.validation.ksm_rpc.success_unset'
          ).toString(),
      error: this.$t('general_settings.validation.ksm_rpc.error').toString()
    };

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

  mounted() {
    this.loadFromState();
  }

  private loadFromState() {
    this.selectedCurrency = this.currency;
    const settings = this.generalSettings;
    this.floatingPrecision = settings.floatingPrecision.toString();
    this.anonymizedLogs = settings.anonymizedLogs;
    this.anonymousUsageAnalytics = settings.anonymousUsageAnalytics;
    this.rpcEndpoint = settings.ethRpcEndpoint;
    this.ksmRpcEndpoint = settings.ksmRpcEndpoint;
    this.balanceSaveFrequency = settings.balanceSaveFrequency.toString();
    this.dateDisplayFormat = settings.dateDisplayFormat;
    this.btcDerivationGapLimit = settings.btcDerivationGapLimit.toString();
    const state = this.$store.state;
    this.scrambleData = state.session.scrambleData;
    this.defaultGraphTimeframe = state.settings![TIMEFRAME_SETTING];
    this.queryPeriod = state.settings![QUERY_PERIOD].toString();
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
}
</style>
