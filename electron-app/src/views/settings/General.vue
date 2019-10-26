<template>
  <div id="settings-general">
    <div class="row">
      <div class="col-lg-12">
        <h1 class="page-header">Settings</h1>
      </div>
    </div>
    <div class="row">
      <div class="col-lg-12">
        <div class="panel panel-default">
          <div class="panel-heading">General Settings</div>
          <div id="general_settings_panel_body" class="panel-body">
            <div class="form-group input-group">
              <span class="input-group-addon">Floating Precision:</span>
              <input
                id="floating_precision"
                v-model="floatingPrecision"
                class="form-control"
                type="number"
              />
            </div>
            <div class="checkbox">
              <label>
                <input
                  id="anonymized_logs_input"
                  v-model="anonymizedLogs"
                  type="checkbox"
                />
                Should logs by anonymized?
              </label>
            </div>
            <div class="form-group input-group">
              <span class="input-group-addon">
                Date from when to count historical data:
              </span>
              <input
                id="historical_data_start"
                v-model="historicDataStart"
                class="form-control"
                type="text"
              />
            </div>
            <div class="form-group">
              <label class="form-prompt">
                Select Main Currency
              </label>
              <select
                id="maincurrencyselector"
                v-model="selectedCurrency"
                class="form-control"
                style="font-family: 'FontAwesome', 'sans-serif';"
              >
                <option v-for="currency in currencies" :value="currency">{{
                  currency
                }}</option>
              </select>
            </div>
            <div class="form-group input-group">
              <span class="input-group-addon">
                Eth RPC Port:
              </span>
              <input
                id="eth_rpc_port"
                v-model="rpcPort"
                class="form-control"
                type="number"
              />
            </div>
            <div class="form-group input-group">
              <span class="input-group-addon">
                Balance data saving frequency in hours:
              </span>
              <input
                id="balance_save_frequency"
                v-model="balanceSaveFrequency"
                class="form-control"
                type="number"
              />
            </div>
            <div class="form-group input-group">
              <span class="input-group-addon">
                Date display format:
              </span>
              <input
                id="date_display_format"
                v-model="dateDisplayFormat"
                class="form-control"
                type="text"
              />
            </div>
            <button
              id="settingssubmit"
              type="submit"
              class="btn btn-default"
              @click="save()"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { currencies } from '@/data/currencies';
import { RotkehlchenState } from '@/store';
import { showError, showInfo } from '@/legacy/utils';
import { settings } from '@/legacy/settings';
import { GeneralSettings } from '@/typing/types';

@Component({})
export default class General extends Vue {
  floatingPrecision: number = 0;
  anonymizedLogs: boolean = false;
  historicDataStart: string = '';
  rpcPort: number = 0;
  balanceSaveFrequency: number = 0;
  dateDisplayFormat: string = '';
  selectedCurrency: string = '';

  get currencies(): string[] {
    return currencies.map(x => x.ticker_symbol);
  }

  mounted() {
    const state = this.$store.state as RotkehlchenState;
    this.selectedCurrency = state.currency.ticker_symbol;
    const settings = state.settings;
    this.floatingPrecision = settings.floatingPrecision;
    this.anonymizedLogs = settings.anonymizedLogs;
    this.historicDataStart = settings.historicDataStart;
    this.rpcPort = settings.rpcPort;
    this.balanceSaveFrequency = settings.balanceSaveFrequency;
    this.dateDisplayFormat = settings.dateDisplayFormat;

    $('#historical_data_start').datetimepicker({
      timepicker: false,
      format: 'd/m/Y'
    });
  }

  save() {
    if (this.rpcPort < 1 || this.rpcPort > 65535) {
      showError(
        'Invalid port number',
        'Please ensure that the specified port number is between 1 and 65535'
      );
      return;
    }
    const payload = {
      ui_floating_precision: this.floatingPrecision,
      historical_data_start: this.historicDataStart,
      main_currency: this.selectedCurrency,
      eth_rpc_port: this.rpcPort,
      balance_save_frequency: this.balanceSaveFrequency,
      anonymized_logs: this.anonymizedLogs,
      date_display_format: this.dateDisplayFormat
    };

    const generalSettings: GeneralSettings = {
      floatingPrecision: this.floatingPrecision,
      historicDataStart: this.historicDataStart,
      rpcPort: this.rpcPort,
      balanceSaveFrequency: this.balanceSaveFrequency,
      anonymizedLogs: this.anonymizedLogs,
      dateDisplayFormat: this.dateDisplayFormat,
      selectedCurrency: this.selectedCurrency
    };

    this.$rpc
      .set_settings(payload)
      .then(result => {
        let message = 'Successfully modified settings.';
        if ('message' in result && result.message !== '') {
          message = ` ${message}${result.message}`;
        }
        showInfo('Success', message);
        this.$store.commit('settings', generalSettings);
      })
      .catch((error: Error) => {
        showError(
          'Settings Error',
          `Error at modifying settings: ${error.message}`
        );
      });
  }
}
</script>

<style scoped></style>
