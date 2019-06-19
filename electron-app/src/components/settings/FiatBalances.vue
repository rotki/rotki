<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-layout>
    <v-flex>
      <v-card>
        <v-toolbar card>Fiat Balances</v-toolbar>
        <v-card-text>
          <v-select
            v-model="selectedCurrency"
            item-value="ticker_symbol"
            item-text="ticker_symbol"
            :items="availableCurrencies"
            label="Currency"
            @change="onChange()"
          ></v-select>
          <v-text-field
            v-model="balance"
            type="number"
            label="Balance"
            prepend-icon="fa-money"
          ></v-text-field>
          <v-btn
            color="primary"
            depressed
            :disabled="!selectedCurrency"
            @click="modify()"
          >
            {{ add ? 'Add Balance' : 'Modify Balance' }}
          </v-btn>
          <v-flex xs12>
            <v-data-table :headers="headers" :items="fiatBalances">
              <template v-slot:items="props">
                <td>
                  {{ props.item.currency }}
                </td>
                <td>
                  {{ props.item.amount | precision(floatingPrecision) }}
                </td>
                <td>
                  {{ props.item.usdValue | precision(floatingPrecision) }}
                </td>
              </template>
            </v-data-table>
          </v-flex>
        </v-card-text>
      </v-card>
    </v-flex>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { Currency } from '@/model/currency';
import { currencies } from '@/data/currencies';
import { mapGetters } from 'vuex';

@Component({
  computed: mapGetters(['floatingPrecision'])
})
export default class FiatBalances extends Vue {
  balance: string = '';
  selectedCurrency: string = '';

  floatingPrecision!: number;

  errorTitle: string = '';
  errorMessage: string = '';

  fiatBalances: { currency: string; amount: number; usdValue: number }[] = [];

  get add(): boolean {
    return (
      this.fiatBalances.findIndex(
        value => value.currency === this.selectedCurrency
      ) === -1
    );
  }

  onChange() {
    const currency = this.selectedCurrency;
    let balance = 0;
    if (currency) {
      const fiatBalance = this.fiatBalances.find(
        value => value.currency === currency
      );
      if (fiatBalance) {
        balance = fiatBalance.amount;
      }
    }
    this.balance = balance.toString();
  }

  headers = [
    { text: 'Currency', value: 'asset' },
    { text: 'Amount', value: 'amount' },
    { text: 'USD Value', value: 'value' }
  ];

  get availableCurrencies(): Currency[] {
    return currencies;
  }

  modify() {
    const currency = this.selectedCurrency;
    const balance = this.balance;
    this.$rpc
      .set_fiat_balance(currency, balance.toString())
      .then(() => {
        this.fetchFiatBalances();
        this.selectedCurrency = '';
        this.balance = '';
      })
      .catch((reason: Error) => {
        this.errorMessage = `Error at modifying ${currency} balance: ${reason.message}`;
        this.errorTitle = 'Balance Modification Error';
      });
  }

  created() {
    this.fetchFiatBalances();
  }

  private fetchFiatBalances() {
    this.$rpc
      .query_fiat_balances()
      .then(value => {
        this.fiatBalances = Object.keys(value).map(currency => ({
          currency: currency,
          amount: parseFloat(value[currency].amount as string),
          usdValue: parseFloat(value[currency].usd_value as string)
        }));
      })
      .catch(reason => {
        console.log(`Error at querying fiat balances: ${reason}`);
      });
  }
}
</script>

<style scoped></style>
