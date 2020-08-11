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
                    exchangePurgeSuccess
                      ? ['Cached data where successfully purged']
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
                      @click="confirmExchangePurge = true"
                    >
                      <v-icon>fa-trash</v-icon>
                    </v-btn>
                  </template>
                  <span>Purge cached data for the selected exchange</span>
                </v-tooltip>
              </v-col>
            </v-row>
            <h3>Ethereum Transactions</h3>
            <v-row align="center">
              <v-col cols="auto">
                <v-btn
                  color="primary"
                  depressed
                  class="data-management__purge-transactions"
                  @click="confirmTransactionPurge = true"
                >
                  Purge ethereum transactions
                </v-btn>
              </v-col>
              <v-col v-if="transactionPurgeSuccess">
                <v-icon color="success">fa-check-circle</v-icon>
                <span
                  class="ml-2 success--text data-management__transactions__message"
                >
                  Ethereum transactions where successfully purged.
                </span>
              </v-col>
              <v-col v-if="transactionPurgeError">
                <v-icon color="error">fa-warning</v-icon>
                <span
                  class="ml-2 error--text data-management__transactions__message"
                >
                  Failed to purge cached ethereum transactions:
                  {{ transactionPurgeError }}.
                </span>
              </v-col>
            </v-row>
          </v-card-text>
        </v-form>
      </v-card>
      <confirm-dialog
        :display="confirmExchangePurge"
        title="Purge cached exchange data"
        :message="`Are you sure you want to purge the cached data for ${exchange}?`"
        @confirm="purgeExchangeData()"
        @cancel="confirmExchangePurge = false"
      />
      <confirm-dialog
        :display="confirmTransactionPurge"
        title="Purge ethereum transaction data"
        :message="`Are you sure you want to purge the cached data for ethereum transactions?`"
        @confirm="purgeEthereumTransactions()"
        @cancel="confirmTransactionPurge = false"
      />
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { exchanges } from '@/data/defaults';
import { SupportedExchange } from '@/services/balances/types';

@Component({
  components: { ConfirmDialog }
})
export default class DataManagement extends Vue {
  exchange: SupportedExchange = exchanges[0];
  exchanges = exchanges;

  confirmExchangePurge: boolean = false;
  confirmTransactionPurge: boolean = false;

  transactionPurgeSuccess: boolean = false;
  exchangePurgeSuccess: boolean = false;

  exchangePurgeError: string[] = [];
  transactionPurgeError: string = '';

  async purgeExchangeData() {
    for (let i = 0; i < this.exchangePurgeError.length; i++) {
      this.exchangePurgeError.pop();
    }

    this.confirmExchangePurge = false;
    const name = this.exchange;
    try {
      await this.$api.balances.deleteExchangeData(name);
      this.exchangePurgeSuccess = true;
      setTimeout(() => {
        this.exchangePurgeSuccess = false;
      }, 5000);
    } catch (e) {
      this.exchangePurgeError.push(
        `Purging cached data for ${name} failed: ${e.message}`
      );
    }
  }

  async purgeEthereumTransactions() {
    this.transactionPurgeError = '';
    this.confirmTransactionPurge = false;
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
