<template>
  <v-container id="settings-general">
    <v-layout>
      <v-flex>
        <h1 class="page-header">Settings</h1>
      </v-flex>
    </v-layout>
    <v-layout>
      <v-flex>
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
              label="Should logs by anonymized?"
            ></v-checkbox>

            <v-menu
              ref="historicDateMenu"
              v-model="historicDateMenu"
              :close-on-content-click="false"
              :nudge-right="40"
              transition="scale-transition"
              offset-y
              full-width
              max-width="290px"
              min-width="290px"
            >
              <template #activator="{ on }">
                <v-text-field
                  id="historical_data_start"
                  v-model="historicDataStart"
                  label="Date from when to count historical data"
                  hint="DD/MM/YYYY format"
                  persistent-hint
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
      </v-flex>
    </v-layout>
    <message-dialog
      title="Settings Error"
      :message="error"
      @dismiss="dismiss()"
    ></message-dialog>
    <message-dialog
      :success="true"
      title="Successfully modified settings."
      :message="success"
      @dismiss="dismiss()"
    ></message-dialog>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { currencies } from '@/data/currencies';
import { GeneralSettings } from '@/typing/types';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';

const { mapState } = createNamespacedHelpers('session');

@Component({
  components: { MessageDialog },
  computed: {
    ...mapState(['settings', 'currency'])
  }
})
export default class General extends Vue {
  settings!: GeneralSettings;
  currency!: Currency;

  floatingPrecision: number = 0;
  anonymizedLogs: boolean = false;
  historicDataStart: string = '';
  rpcEndpoint: string = 'http://localhost:8546';
  balanceSaveFrequency: number = 0;
  dateDisplayFormat: string = '';
  selectedCurrency: string = '';

  historicDateMenu: boolean = false;
  date: string = '';

  error: string = '';
  success: string = '';

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
    if (!date) return null;

    const [day, month, year] = date.split('/');
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }

  get currencies(): string[] {
    return currencies.map(x => x.ticker_symbol);
  }

  dismiss() {
    this.success = '';
    this.error = '';
  }

  mounted() {
    this.selectedCurrency = this.currency.ticker_symbol;
    const settings = this.settings;
    this.floatingPrecision = settings.floatingPrecision;
    this.anonymizedLogs = settings.anonymizedLogs;
    this.historicDataStart = settings.historicDataStart;
    this.rpcEndpoint = settings.ethRpcEndpoint;
    this.balanceSaveFrequency = settings.balanceSaveFrequency;
    this.dateDisplayFormat = settings.dateDisplayFormat;
    this.date = this.parseDate(settings.historicDataStart) || '';
  }

  save() {
    const payload = {
      ui_floating_precision: this.floatingPrecision,
      historical_data_start: this.historicDataStart,
      main_currency: this.selectedCurrency,
      eth_rpc_endpoint: this.rpcEndpoint,
      balance_save_frequency: this.balanceSaveFrequency,
      anonymized_logs: this.anonymizedLogs,
      date_display_format: this.dateDisplayFormat
    };

    const generalSettings: GeneralSettings = {
      floatingPrecision: this.floatingPrecision,
      historicDataStart: this.historicDataStart,
      ethRpcEndpoint: this.rpcEndpoint,
      balanceSaveFrequency: this.balanceSaveFrequency,
      anonymizedLogs: this.anonymizedLogs,
      dateDisplayFormat: this.dateDisplayFormat,
      selectedCurrency: this.selectedCurrency
    };

    this.$rpc
      .set_settings(payload)
      .then(result => {
        this.success = result.message || '';
        this.$store.commit('session/settings', generalSettings);
      })
      .catch((error: Error) => {
        this.error = `Error at modifying settings: ${error.message}`;
      });
  }
}
</script>

<style scoped></style>
