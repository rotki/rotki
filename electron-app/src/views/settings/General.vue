<template>
  <v-container id="settings-general">
    <v-row>
      <v-col>
        <h1 class="page-header">Settings</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>General Settings</v-card-title>
          <v-card-text>
            <v-text-field
              id="floating_precision"
              v-model="floatingPrecision"
              label="Floating Precision"
              type="number"
            ></v-text-field>

            <v-checkbox
              id="anonymized_logs_input"
              v-model="anonymizedLogs"
              off-icon="fa fa-square-o"
              label="Should logs by anonymized?"
            ></v-checkbox>

            <v-checkbox
              id="anonymous_usage_analytics"
              v-model="anonymousUsageAnalytics"
              off-icon="fa fa-square-o"
              label="Should anonymous usage analytics be submitted?"
            ></v-checkbox>

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
                  id="historical_data_start"
                  v-model="historicDataStart"
                  label="Date from when to count historical data"
                  hint="DD/MM/YYYY format"
                  prepend-icon="fa-calendar"
                  @blur="date = parseDate(historicDataStart)"
                  v-on="on"
                ></v-text-field>
              </template>
              <v-date-picker
                v-model="date"
                no-title
                @input="historicDateMenu = false"
              ></v-date-picker>
            </v-menu>

            <v-select
              id="maincurrencyselector"
              v-model="selectedCurrency"
              label="Select Main Currency"
              item-text="ticker_symbol"
              return-object
              :items="currencies"
            >
            </v-select>

            <v-text-field
              id="eth_rpc_endpoint"
              v-model="rpcEndpoint"
              label="Eth RPC Endpoint"
              type="text"
              data-vv-name="eth_rpc_endpoint"
            ></v-text-field>

            <v-text-field
              id="balance_save_frequency"
              v-model="balanceSaveFrequency"
              label="Balance data saving frequency in hours"
              type="number"
            ></v-text-field>

            <v-text-field
              id="date_display_format"
              v-model="dateDisplayFormat"
              label="Date display format"
              type="text"
            ></v-text-field>
          </v-card-text>

          <v-card-actions>
            <v-btn
              id="settingssubmit"
              depressed
              color="primary"
              type="submit"
              @click="save()"
            >
              Save
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { currencies } from '@/data/currencies';
import { GeneralSettings, SettingsUpdate } from '@/typing/types';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';
import { Message } from '@/store/store';
import { convertToGeneralSettings } from '@/data/converters';

const { mapState, mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { MessageDialog },
  computed: {
    ...mapState(['settings']),
    ...mapGetters(['currency'])
  }
})
export default class General extends Vue {
  settings!: GeneralSettings;
  currency!: Currency;

  floatingPrecision: string = '0';
  anonymizedLogs: boolean = false;
  anonymousUsageAnalytics: boolean = false;
  historicDataStart: string = '';
  rpcEndpoint: string = 'http://localhost:8545';
  balanceSaveFrequency: string = '0';
  dateDisplayFormat: string = '';
  selectedCurrency: Currency = currencies[0];

  historicDateMenu: boolean = false;
  date: string = '';

  @Watch('date')
  dateWatch() {
    this.historicDataStart = this.formatDate(this.date);
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
    const settings = this.settings;
    this.floatingPrecision = settings.floatingPrecision.toString();
    this.anonymizedLogs = settings.anonymizedLogs;
    this.anonymousUsageAnalytics = settings.anonymousUsageAnalytics;
    this.historicDataStart = settings.historicDataStart;
    this.rpcEndpoint = settings.ethRpcEndpoint;
    this.balanceSaveFrequency = settings.balanceSaveFrequency.toString();
    this.dateDisplayFormat = settings.dateDisplayFormat;
    this.date = this.parseDate(settings.historicDataStart) || '';
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
        this.settings.floatingPrecision
      ),
      historical_data_start: setOnlyIfDifferent(
        this.historicDataStart,
        this.settings.historicDataStart
      ),
      main_currency: setOnlyIfDifferent(
        this.selectedCurrency.ticker_symbol,
        this.currency.ticker_symbol
      ),
      eth_rpc_endpoint: setOnlyIfDifferent(
        this.rpcEndpoint,
        this.settings.ethRpcEndpoint
      ),
      balance_save_frequency: setOnlyIfDifferent(
        balanceSaveFrequency,
        this.settings.balanceSaveFrequency
      ),
      anonymized_logs: setOnlyIfDifferent(
        this.anonymizedLogs,
        this.settings.anonymizedLogs
      ),
      submit_usage_analytics: setOnlyIfDifferent(
        this.anonymousUsageAnalytics,
        this.settings.anonymousUsageAnalytics
      ),
      date_display_format: setOnlyIfDifferent(
        this.dateDisplayFormat,
        this.settings.dateDisplayFormat
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
        commit('session/settings', convertToGeneralSettings(settings));
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
