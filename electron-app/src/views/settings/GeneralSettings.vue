<template>
  <v-container id="settings-general">
    <v-row no-gutters>
      <v-col>
        <v-card>
          <v-card-title>General Settings</v-card-title>
          <v-card-text>
            <v-text-field
              v-model="floatingPrecision"
              class="settings-general__fields__floating-precision"
              label="Floating Precision"
              type="number"
              :success-messages="settingsMessages['floatingPrecision'].success"
              :error-messages="settingsMessages['floatingPrecision'].error"
              @change="onFloatingPrecisionChange($event)"
            ></v-text-field>
            <v-switch
              v-model="anonymizedLogs"
              class="settings-general__fields__anonymized-logs"
              label="Should logs be anonymized?"
              color="primary"
              :success-messages="settingsMessages['anonymizedLogs'].success"
              :error-messages="settingsMessages['anonymizedLogs'].error"
              @change="onAnonymizedLogsChange($event)"
            ></v-switch>
            <v-switch
              v-model="anonymousUsageAnalytics"
              class="settings-general__fields__anonymous-usage-statistics"
              color="primary"
              label="Should anonymous usage analytics be submitted?"
              :success-messages="
                settingsMessages['anonymousUsageAnalytics'].success
              "
              :error-messages="
                settingsMessages['anonymousUsageAnalytics'].error
              "
              @change="onAnonymousUsageAnalyticsChange($event)"
            ></v-switch>
            <v-menu
              ref="historicDateMenu"
              v-model="historicDateMenu"
              :close-on-content-click="false"
              :nudge-right="40"
              transition="scale-transition"
              offset-y
              max-width="290px"
              min-width="290px"
            >
              <template #activator="{ on }">
                <v-text-field
                  v-model="historicDataStart"
                  class="settings-general__fields__historic-data-start"
                  label="Date from when to count historical data"
                  hint="DD/MM/YYYY format"
                  prepend-icon="fa-calendar"
                  :success-messages="
                    settingsMessages['historicDataStart'].success
                  "
                  :error-messages="settingsMessages['historicDataStart'].error"
                  readonly
                  v-on="on"
                  @change="onHistoricDataStartChange($event)"
                ></v-text-field>
              </template>
              <v-date-picker
                v-model="date"
                no-title
                @input="historicDateMenu = false"
              ></v-date-picker>
            </v-menu>

            <v-select
              v-model="selectedCurrency"
              class="settings-general__fields__currency-selector"
              label="Select Main Currency"
              item-text="ticker_symbol"
              return-object
              :items="currencies"
              :success-messages="settingsMessages['selectedCurrency'].success"
              :error-messages="settingsMessages['selectedCurrency'].error"
              @change="onSelectedCurrencyChange($event)"
            >
              <template #item="{ item, attrs, on }">
                <v-list-item
                  :id="`currency__${item.ticker_symbol.toLocaleLowerCase()}`"
                  v-bind="attrs"
                  v-on="on"
                >
                  {{ item.ticker_symbol }}
                </v-list-item>
              </template>
            </v-select>

            <v-text-field
              v-model="rpcEndpoint"
              class="settings-general__fields__rpc-endpoint"
              label="Eth RPC Endpoint"
              type="text"
              data-vv-name="eth_rpc_endpoint"
              :success-messages="settingsMessages['rpcEndpoint'].success"
              :error-messages="settingsMessages['rpcEndpoint'].error"
              @change="onRpcEndpointChange($event)"
            ></v-text-field>

            <v-text-field
              v-model="balanceSaveFrequency"
              class="settings-general__fields__balance-save-frequency"
              label="Balance data saving frequency in hours"
              type="number"
              :success-messages="
                settingsMessages['balanceSaveFrequency'].success
              "
              :error-messages="settingsMessages['balanceSaveFrequency'].error"
              @change="onBalanceSaveFrequencyChange($event)"
            ></v-text-field>

            <v-text-field
              v-model="dateDisplayFormat"
              class="settings-general__fields__date-display-format"
              label="Date display format"
              type="text"
              :success-messages="settingsMessages['dateDisplayFormat'].success"
              :error-messages="settingsMessages['dateDisplayFormat'].error"
              @change="onDateDisplayFormatChange($event)"
            ></v-text-field>
          </v-card-text>
        </v-card>
        <v-card class="mt-5">
          <v-card-title>Frontend-only Settings</v-card-title>
          <v-card-text>
            <v-switch
              v-model="scrambleData"
              class="settings-general__fields__scramble-data"
              :label="`Scramble data. Use this when sharing screenshots with others, e.g. when filing bug reports. NOTE: This setting does not persist between sessions.`"
              :success-messages="settingsMessages['scrambleData'].success"
              :error-messages="settingsMessages['scrambleData'].error"
              @change="onScrambleDataChange($event)"
            >
            </v-switch>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Watch } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { convertToGeneralSettings, findCurrency } from '@/data/converters';
import { currencies } from '@/data/currencies';
import { Currency } from '@/model/currency';
import { Message } from '@/store/store';
import { GeneralSettings, SettingsUpdate } from '@/typing/types';
import Settings, { SettingsMessages } from '@/views/settings/Settings.vue';

const { mapState, mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { MessageDialog, RevealableInput },
  computed: {
    ...mapState(['generalSettings']),
    ...mapGetters(['currency'])
  }
})
export default class General extends Settings {
  generalSettings!: GeneralSettings;
  currency!: Currency;

  floatingPrecision: string = '0';
  anonymizedLogs: boolean = false;
  anonymousUsageAnalytics: boolean = false;
  historicDataStart: string = '';
  rpcEndpoint: string = 'http://localhost:8545';
  balanceSaveFrequency: string = '0';
  dateDisplayFormat: string = '';
  selectedCurrency: Currency = currencies[0];
  scrambleData: boolean = false;

  settingsMessages: SettingsMessages = {
    floatingPrecision: { success: '', error: '' },
    anonymizedLogs: { success: '', error: '' },
    anonymousUsageAnalytics: { success: '', error: '' },
    historicDataStart: { success: '', error: '' },
    rpcEndpoint: { success: '', error: '' },
    balanceSaveFrequency: { success: '', error: '' },
    dateDisplayFormat: { success: '', error: '' },
    selectedCurrency: { success: '', error: '' },
    scrambleData: { success: '', error: '' }
  };

  historicDateMenu: boolean = false;
  date: string = '';

  @Watch('date')
  dateWatch() {
    const date = this.formatDate(this.date);
    if (this.historicDataStart !== date) {
      this.historicDataStart = date;
      this.onHistoricDataStartChange(this.historicDataStart);
    }
  }

  onScrambleDataChange(enabled: boolean) {
    const { commit } = this.$store;
    const previousValue = this.$store.state.session.scrambleData;

    try {
      commit('session/scrambleData', enabled);
      this.validateSettingChange('scrambleData', 'success');
    } catch (error) {
      this.validateSettingChange(
        'anonymizedLogs',
        'error',
        `Error setting anonymized logs ${error}`
      );
      this.scrambleData = previousValue;
    }
  }

  onSelectedCurrencyChange(currency: Currency) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ main_currency: currency.ticker_symbol })
      .then(settings => {
        commit('session/generalSettings', {
          ...this.generalSettings,
          selectedCurrency: findCurrency(settings.main_currency)
        });
        this.validateSettingChange(
          'selectedCurrency',
          'success',
          `Main currency set to ${currency.ticker_symbol}`
        );
      })
      .catch(reason => {
        this.validateSettingChange(
          'selectedCurrency',
          'error',
          `Error setting main currency ${reason.message}`
        );
      });
  }

  onFloatingPrecisionChange(precision: string) {
    const { commit } = this.$store;
    const previousValue = this.generalSettings.floatingPrecision.toString();

    if (this.execOnlyIfDifferent(precision, previousValue)) {
      this.$api
        .setSettings({ ui_floating_precision: parseInt(precision) })
        .then(settings => {
          commit('session/generalSettings', {
            ...this.generalSettings,
            floatingPrecision: settings.ui_floating_precision
          });
          this.validateSettingChange(
            'floatingPrecision',
            'success',
            `Floating precision set to ${precision}`
          );
        })
        .catch(reason => {
          this.validateSettingChange(
            'floatingPrecision',
            'error',
            `Error setting floating precision to ${precision}. ${reason.message}`
          );
          this.floatingPrecision = previousValue;
        });
    }
  }

  onAnonymizedLogsChange(enabled: boolean) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ anonymized_logs: enabled })
      .then(settings => {
        commit('session/generalSettings', {
          ...this.generalSettings,
          anonymizedLogs: settings.anonymized_logs
        });
        this.validateSettingChange('anonymizedLogs', 'success');
      })
      .catch(reason => {
        this.validateSettingChange(
          'anonymizedLogs',
          'error',
          `Error setting anonymized logs ${reason.message}`
        );
      });
  }

  onAnonymousUsageAnalyticsChange(enabled: boolean) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ submit_usage_analytics: enabled })
      .then(settings => {
        commit('session/generalSettings', {
          ...this.generalSettings,
          anonymousUsageAnalytics: settings.submit_usage_analytics
        });
        this.validateSettingChange('anonymousUsageAnalytics', 'success');
      })
      .catch(reason => {
        this.validateSettingChange(
          'anonymousUsageAnalytics',
          'error',
          `Error setting anonymous usage analytics ${reason.message}`
        );
      });
  }

  onHistoricDataStartChange(date: string) {
    const { commit } = this.$store;
    const previousValue = this.parseDate(
      this.generalSettings.historicDataStart
    );

    if (this.execOnlyIfDifferent(date, previousValue)) {
      this.$api
        .setSettings({ historical_data_start: date })
        .then(settings => {
          commit('session/generalSettings', {
            ...this.generalSettings,
            historicDataStart: settings.historical_data_start
          });
          this.validateSettingChange(
            'historicDataStart',
            'success',
            `Historical data start set to ${date}`
          );
        })
        .catch(reason => {
          this.validateSettingChange(
            'historicDataStart',
            'error',
            `Error setting historical data start to ${date}. ${reason.message}`
          );
          this.historicDataStart = previousValue || '';
        });
    }
  }

  onBalanceSaveFrequencyChange(frequency: string) {
    const { commit } = this.$store;
    const previousValue = this.generalSettings.balanceSaveFrequency;

    if (this.execOnlyIfDifferent(frequency, String(previousValue))) {
      this.$api
        .setSettings({ balance_save_frequency: parseInt(frequency) })
        .then(settings => {
          commit('session/generalSettings', {
            ...this.generalSettings,
            balanceSaveFrequency: settings.balance_save_frequency
          });
          this.validateSettingChange(
            'balanceSaveFrequency',
            'success',
            `data save frequency set to ${frequency} hours`
          );
        })
        .catch(reason => {
          this.validateSettingChange(
            'balanceSaveFrequency',
            'error',
            `Error setting balance save frequency to ${frequency}. ${reason.message}`
          );
          this.balanceSaveFrequency = String(previousValue);
        });
    }
  }

  onDateDisplayFormatChange(dateFormat: string) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ date_display_format: dateFormat })
      .then(settings => {
        commit('session/generalSettings', {
          ...this.generalSettings,
          dateDisplayFormat: settings.date_display_format
        });
        this.validateSettingChange(
          'dateDisplayFormat',
          'success',
          `date display set to ${dateFormat}`
        );
      })
      .catch(reason => {
        this.validateSettingChange(
          'dateDisplayFormat',
          'error',
          `Error setting date display format ${reason.message}`
        );
      });
  }

  onRpcEndpointChange(endpoint: string) {
    const { commit } = this.$store;
    const previousValue = this.parseDate(this.generalSettings.ethRpcEndpoint);

    if (this.execOnlyIfDifferent(endpoint, previousValue)) {
      this.$api
        .setSettings({ eth_rpc_endpoint: endpoint })
        .then(settings => {
          commit('session/generalSettings', {
            ...this.generalSettings,
            rpcEndpoint: settings.eth_rpc_endpoint
          });
          this.validateSettingChange(
            'rpcEndpoint',
            'success',
            `RPC endpoint set to ${endpoint}`
          );
        })
        .catch(reason => {
          this.validateSettingChange(
            'rpcEndpoint',
            'error',
            `Error setting rpc endpoint ${reason.message}`
          );
          this.rpcEndpoint = previousValue || 'http://localhost:8545';
        });
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
    this.historicDataStart = settings.historicDataStart;
    this.rpcEndpoint = settings.ethRpcEndpoint;
    this.balanceSaveFrequency = settings.balanceSaveFrequency.toString();
    this.dateDisplayFormat = settings.dateDisplayFormat;
    this.date = this.parseDate(settings.historicDataStart) || '';
    this.scrambleData = this.$store.state.session.scrambleData;
  }

  execOnlyIfDifferent<T>(value: T, oldValue: T): T | undefined {
    return value !== oldValue ? value : undefined;
  }

  save() {
    function setOnlyIfDifferent<T>(value: T, oldValue: T): T | undefined {
      return value !== oldValue ? value : undefined;
    }

    const { commit } = this.$store;

    const floatingPrecision = parseInt(this.floatingPrecision);
    const balanceSaveFrequency = parseInt(this.balanceSaveFrequency);

    const update: SettingsUpdate = {
      ui_floating_precision: setOnlyIfDifferent(
        floatingPrecision,
        this.generalSettings.floatingPrecision
      ),
      historical_data_start: setOnlyIfDifferent(
        this.historicDataStart,
        this.generalSettings.historicDataStart
      ),
      main_currency: setOnlyIfDifferent(
        this.selectedCurrency.ticker_symbol,
        this.currency.ticker_symbol
      ),
      eth_rpc_endpoint: setOnlyIfDifferent(
        this.rpcEndpoint,
        this.generalSettings.ethRpcEndpoint
      ),
      balance_save_frequency: setOnlyIfDifferent(
        balanceSaveFrequency,
        this.generalSettings.balanceSaveFrequency
      ),
      anonymized_logs: setOnlyIfDifferent(
        this.anonymizedLogs,
        this.generalSettings.anonymizedLogs
      ),
      submit_usage_analytics: setOnlyIfDifferent(
        this.anonymousUsageAnalytics,
        this.generalSettings.anonymousUsageAnalytics
      ),
      date_display_format: setOnlyIfDifferent(
        this.dateDisplayFormat,
        this.generalSettings.dateDisplayFormat
      )
    };
    this.$api
      .setSettings(update)
      .then(settings => {
        commit('setMessage', {
          title: 'Success',
          description: 'Successfully changed settings.',
          success: true
        } as Message);
        commit('session/generalSettings', convertToGeneralSettings(settings));
        this.loadFromState();
      })
      .catch((error: Error) => {
        this.loadFromState();
        commit('setMessage', {
          title: 'Settings Error',
          description: `Error at changing settings: ${error.message}`
        } as Message);
      });
  }
}
</script>

<style scoped></style>
