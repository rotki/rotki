<template>
  <v-container id="settings-general">
    <v-row>
      <v-col>
        <h1>Settings</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>General Settings</v-card-title>
          <v-card-text>
            <v-text-field
              v-model="floatingPrecision"
              class="settings-general__fields__floating-precision"
              label="Floating Precision"
              type="number"
            ></v-text-field>

            <v-checkbox
              v-model="anonymizedLogs"
              class="settings-general__fields__anonymized-logs"
              off-icon="fa fa-square-o"
              label="Should logs be anonymized?"
            ></v-checkbox>

            <v-checkbox
              v-model="anonymousUsageAnalytics"
              class="settings-general__fields__anonymous-usage-statistics"
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
                  v-model="historicDataStart"
                  class="settings-general__fields__historic-data-start"
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
              v-model="selectedCurrency"
              class="settings-general__fields__currency-selector"
              label="Select Main Currency"
              item-text="ticker_symbol"
              return-object
              :items="currencies"
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
            ></v-text-field>

            <v-text-field
              v-model="balanceSaveFrequency"
              class="settings-general__fields__balance-save-frequency"
              label="Balance data saving frequency in hours"
              type="number"
            ></v-text-field>

            <v-text-field
              v-model="dateDisplayFormat"
              class="settings-general__fields__date-display-format"
              label="Date display format"
              type="text"
            ></v-text-field>
          </v-card-text>

          <v-card-actions>
            <v-btn
              depressed
              class="settings-general__buttons__save"
              color="primary"
              type="submit"
              @click="save()"
            >
              Save
            </v-btn>
          </v-card-actions>
        </v-card>
        <v-card class="mt-5">
          <v-card-title>Frontend-only Settings</v-card-title>
          <v-card-text>
            <v-switch
              v-model="scrambleData"
              class="settings-general__fields__scramble-data"
              :label="`Scramble data. Use this when sharing screenshots with others, e.g. when filing bug reports. NOTE: This setting does not persist between sessions.`"
            >
            </v-switch>
          </v-card-text>
        </v-card>
        <v-card class="mt-5">
          <v-card-title>User Account & Security</v-card-title>
          <v-form ref="form">
            <v-card-text>
              <revealable-input
                v-model="currentPassword"
                class="settings-general__account-and-security__fields__current-password"
                label="Current Password"
                :rules="passwordRules"
              ></revealable-input>
              <revealable-input
                v-model="newPassword"
                class="settings-general__account-and-security__fields__new-password"
                label="New Password"
                :rules="passwordRules"
              ></revealable-input>
              <revealable-input
                v-model="newPasswordConfirm"
                class="settings-general__account-and-security__fields__new-password-confirm"
                label="Confirm New Password"
                icon="fa-repeat"
                :rules="passwordConfirmRules"
                :error-messages="errorMessages"
              ></revealable-input>
            </v-card-text>
            <v-card-actions>
              <v-btn
                depressed
                class="settings-general__account-and-security__buttons__change-password"
                color="primary"
                :disabled="
                  !(
                    currentPassword &&
                    newPassword &&
                    newPassword === newPasswordConfirm
                  )
                "
                @click="changePassword()"
              >
                Change Password
              </v-btn>
            </v-card-actions>
          </v-form>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { convertToGeneralSettings } from '@/data/converters';
import { currencies } from '@/data/currencies';
import { Currency } from '@/model/currency';
import { Message } from '@/store/store';
import { GeneralSettings, SettingsUpdate } from '@/typing/types';

const { mapState, mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { MessageDialog, RevealableInput },
  computed: {
    ...mapState(['settings', 'username']),
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

  currentPassword: string = '';
  newPassword: string = '';
  newPasswordConfirm: string = '';
  errorMessages: string[] = [];
  username!: string;

  readonly passwordRules = [(v: string) => !!v || 'Please provide a password'];
  readonly passwordConfirmRules = [
    (v: string) => !!v || 'Please provide a password confirmation'
  ];

  private updateConfirmationError() {
    if (this.errorMessages.length > 0) {
      return;
    }
    this.errorMessages.push(
      'The password confirmation does not match the provided password'
    );
  }

  @Watch('newPassword')
  onNewPasswordChange() {
    if (this.newPassword && this.newPassword !== this.newPasswordConfirm) {
      this.updateConfirmationError();
    } else {
      this.errorMessages.pop();
    }
  }

  @Watch('newPasswordConfirm')
  onNewPasswordConfirmationChange() {
    if (
      this.newPasswordConfirm &&
      this.newPasswordConfirm !== this.newPassword
    ) {
      this.updateConfirmationError();
    } else {
      this.errorMessages.pop();
    }
  }

  historicDateMenu: boolean = false;
  date: string = '';

  @Watch('date')
  dateWatch() {
    this.historicDataStart = this.formatDate(this.date);
  }

  get scrambleData() {
    return this.$store.state.session.scrambleData;
  }

  set scrambleData(value: boolean) {
    this.$store.commit('session/scrambleData', value);
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

  changePassword() {
    const currentPassword = this.currentPassword;
    const newPassword = this.newPassword;
    const newPasswordConfirm = this.newPasswordConfirm;

    if (currentPassword && newPassword === newPasswordConfirm) {
      const { commit } = this.$store;

      this.$api
        .changeUserPassword(this.username, currentPassword, newPassword)
        .then(() => {
          commit('setMessage', {
            title: 'Success',
            description: 'Successfully changed user password',
            success: true
          } as Message);
          (this.$refs.form as Vue & { reset: () => boolean }).reset();
          (this.$refs.form as Vue & {
            resetValidation: () => boolean;
          }).resetValidation();
        })
        .catch((reason: Error) => {
          commit('setMessage', {
            title: 'Error',
            description: reason.message || 'Error while changing user password',
            success: false
          } as Message);
        });
    }
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
