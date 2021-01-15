<template>
  <v-row no-gutters>
    <v-col>
      <v-card>
        <v-card-title v-text="$t('data_management.title')" />
        <v-card-subtitle v-text="$t('data_management.subtitle')" />
        <v-form ref="form">
          <v-card-text>
            <div
              class="title"
              v-text="$t('data_management.exchange_data.title')"
            />
            <v-row align="center">
              <v-col>
                <v-select
                  v-model="exchange"
                  class="data-management__fields__exchange"
                  :items="exchanges"
                  :success-messages="purgeSuccessMessages"
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
                  <span
                    v-text="$t('data_management.exchange_data.purge_tooltip')"
                  />
                </v-tooltip>
              </v-col>
            </v-row>
            <status-button
              class="data-management__purge-all-exchange"
              :tooltip="$t('data_management.exchange_data.purge_all_tooltip')"
              :success-message="purgeAllSuccessMessage"
              :error-message="purgeAllErrorMessage"
              @click="confirmationType = 'exchanges'"
            >
              {{ $t('data_management.exchange_data.purge_all_button') }}
            </status-button>
            <div
              class="title"
              v-text="$t('data_management.ethereum_transactions.title')"
            />
            <status-button
              class="data-management__purge-transactions"
              :tooltip="
                $t('data_management.ethereum_transactions.purge_tooltip')
              "
              :success-message="transactionPurgeSuccessMessage"
              :error-message="transactionPurgeErrorMessage"
              @click="confirmationType = 'transactions'"
            >
              {{ $t('data_management.ethereum_transactions.purge_button') }}
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
import { SUPPORTED_EXCHANGES } from '@/data/defaults';
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
  exchange: SupportedExchange = SUPPORTED_EXCHANGES[0];
  exchanges = SUPPORTED_EXCHANGES;

  transactionPurgeSuccess: boolean = false;
  exchangePurgeSuccess: SupportedExchange | '' = '';
  allExchangePurgeSuccess: boolean = false;

  exchangePurgeError: string[] = [];
  transactionPurgeError: string = '';
  allExchangePurgeError: string = '';

  confirmationType: ConfirmationType = '';

  get purgeSuccessMessages(): string[] {
    const exchangePurgeSuccess = this.exchangePurgeSuccess;
    if (exchangePurgeSuccess) {
      const message = this.$t('data_management.exchange_data.purge_success', {
        exchangePurgeSuccess
      });
      return [message.toString()];
    }
    return [];
  }

  get purgeAllSuccessMessage(): string | null {
    return this.allExchangePurgeSuccess
      ? this.$t('data_management.exchange_data.purge_all_success').toString()
      : null;
  }

  get purgeAllErrorMessage(): string | null {
    return this.allExchangePurgeError
      ? this.$t('data_management.exchange_data.purge_all_error').toString()
      : null;
  }

  get transactionPurgeSuccessMessage(): string | null {
    return this.transactionPurgeSuccess
      ? this.$t(
          'data_management.ethereum_transactions.purge_success'
        ).toString()
      : null;
  }

  get transactionPurgeErrorMessage(): string | null {
    return this.transactionPurgeError
      ? this.$t('data_management.ethereum_transactions.purge_error').toString()
      : null;
  }

  readonly confirmations: AllConfirmations = {
    transactions: {
      title: this.$t('data_management.confirm.transactions.title').toString(),
      message: this.$t(
        'data_management.confirm.transactions.message'
      ).toString(),
      confirm: this.purgeEthereumTransactions
    },
    exchanges: {
      title: this.$t('data_management.confirm.all_exchanges.title').toString(),
      message: this.$t(
        'data_management.confirm.all_exchanges.message'
      ).toString(),
      confirm: this.purgeAllExchangeData
    },
    single: {
      title: this.$t('data_management.confirm.exchange.title').toString(),
      message: this.$t('data_management.confirm.exchange.message').toString(),
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
        this.$t('data_management.errors.exchange', {
          name,
          message: e.message
        }).toString()
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
      this.allExchangePurgeError = this.$t(
        'data_management.errors.all_exchanges',
        { message: e.message }
      ).toString();
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
      this.transactionPurgeError = this.$t(
        'data_management.errors.transactions',
        { message: e.message }
      ).toString();
    }
  }
}
</script>
