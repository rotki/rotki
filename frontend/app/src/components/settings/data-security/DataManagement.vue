<template>
  <v-row no-gutters>
    <v-col>
      <v-card>
        <v-card-title>Manage Data</v-card-title>
        <v-card-subtitle>
          Allows you to purge data cached by rotki
        </v-card-subtitle>
        <v-form ref="form">
          <v-card-text>
            <h3>Exchange Data</h3>
            <v-row align="center">
              <v-col>
                <v-select
                  v-model="exchange"
                  class="data-management__fields__exchange"
                  :items="exchanges"
                  :success-messages="
                    !!exchangePurgeSuccess
                      ? [
                          `Cached data for ${exchangePurgeSuccess} were successfully purged.`
                        ]
                      : []
                  "
                  :error-messages="exchangePurgeError"
                  label="Exchange"
                >
                  <template #item="{ item, attrs, on }">
                    <v-list-item
                      :class="`exchange__${item}`"
                      v-bind="attrs"
                      v-on="on"
                    >
                      {{ item }}
                    </v-list-item>
                  </template>
                </v-select>
              </v-col>
              <v-col cols="auto">
                <v-tooltip top>
                  <template #activator="{ on, attrs }">
                    <v-btn
                      class="data-management__purge-exchange"
                      icon
                      :disabled="!!!exchange"
                      v-bind="attrs"
                      v-on="on"
                      @click="confirmationType = 'single'"
                    >
                      <v-icon>mdi-delete</v-icon>
                    </v-btn>
                  </template>
                  <span>Purge cached data for the selected exchange</span>
                </v-tooltip>
              </v-col>
            </v-row>
            <status-button
              class="data-management__purge-all-exchange"
              tooltip="Purge all the cached exchange data. (deposits/withdrawals/trades)"
              :success-message="
                allExchangePurgeSuccess
                  ? 'Cached data for all the available exchanges were successfully purged.'
                  : null
              "
              :error-message="
                !!allExchangePurgeError
                  ? `Failed to purge cached data for all the exchanges: ${allExchangePurgeError}`
                  : null
              "
              @click="confirmationType = 'exchanges'"
            >
              Purge All Exchanges Cache
            </status-button>
            <h3>Ethereum Transactions</h3>
            <status-button
              class="data-management__purge-transactions"
              tooltip="Purge the cached ethereum data"
              :success-message="
                transactionPurgeSuccess
                  ? 'Ethereum transaction data were successfully purged.'
                  : null
              "
              :error-message="
                !!transactionPurgeError
                  ? `Failed to purge cached ethereum transaction data: ${transactionPurgeError}`
                  : null
              "
              @click="confirmationType = 'transactions'"
            >
              Purge transaction cache
            </status-button>
          </v-card-text>
        </v-form>
      </v-card>
      <confirm-dialog
        v-if="!!confirmationType"
        display
        :title="confirmations[confirmationType].title"
        :message="confirmations[confirmationType].message"
        @confirm="confirmations[confirmationType].confirm"
        @cancel="confirmationType = ''"
      />
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import StatusButton from '@/components/settings/data-security/StatusButton.vue';
import { exchanges } from '@/data/defaults';
import { SupportedExchange } from '@/services/balances/types';

type ConfirmationData = {
  readonly title: string;
  readonly message: string;
  readonly confirm: () => Promise<void>;
};

type AllConfirmations = { [key: string]: ConfirmationData };

type ConfirmationType = 'transactions' | 'exchanges' | 'single' | '';

@Component({
  components: { StatusButton, ConfirmDialog }
})
export default class DataManagement extends Vue {
  exchange: SupportedExchange = exchanges[0];
  exchanges = exchanges;

  transactionPurgeSuccess: boolean = false;
  exchangePurgeSuccess: SupportedExchange | '' = '';
  allExchangePurgeSuccess: boolean = false;

  exchangePurgeError: string[] = [];
  transactionPurgeError: string = '';
  allExchangePurgeError: string = '';

  confirmationType: ConfirmationType = '';

  readonly confirmations: AllConfirmations = {
    transactions: {
      title: 'Purge ethereum transaction data',
      message:
        'Are you sure you want to purge the cached data for ethereum transactions?',
      confirm: this.purgeEthereumTransactions
    },
    exchanges: {
      title: 'Purge all cached exchange data',
      message:
        'Are you sure you want to purge the cached data for all the exchanges?',
      confirm: this.purgeAllExchangeData
    },
    single: {
      title: 'Purge cached exchange data',
      message:
        'Are you sure you want to purge the cached data for the selected exchange?',
      confirm: this.purgeExchangeData
    }
  };

  async purgeExchangeData() {
    for (let i = 0; i < this.exchangePurgeError.length; i++) {
      this.exchangePurgeError.pop();
    }

    this.confirmationType = '';
    const name = this.exchange;
    try {
      await this.$api.balances.deleteExchangeData(name);
      this.exchangePurgeSuccess = name;
      setTimeout(() => {
        this.exchangePurgeSuccess = '';
      }, 5000);
    } catch (e) {
      this.exchangePurgeError.push(
        `Purging cached data for ${name} failed: ${e.message}`
      );
    }
  }

  async purgeAllExchangeData() {
    this.confirmationType = '';
    try {
      await this.$api.balances.deleteExchangeData();
      this.allExchangePurgeSuccess = true;
      setTimeout(() => {
        this.allExchangePurgeSuccess = false;
      }, 5000);
    } catch (e) {
      this.allExchangePurgeError = `Purging the cached data for all the exchanges failed: ${e.message}`;
    }
  }

  async purgeEthereumTransactions() {
    this.transactionPurgeError = '';
    this.confirmationType = '';
    try {
      await this.$api.balances.deleteEthereumTransactions();
      this.transactionPurgeSuccess = true;
      setTimeout(() => {
        this.transactionPurgeSuccess = false;
      }, 5000);
    } catch (e) {
      this.transactionPurgeError = `Purging ethereum transaction cached data failed: ${e.message}`;
    }
  }
}
</script>
