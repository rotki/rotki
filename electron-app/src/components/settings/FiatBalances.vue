<template>
  <v-layout>
    <v-flex>
      <v-card>
        <v-card-title>Fiat Balances</v-card-title>
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
              <template #header.usdValue>
                {{ currency.ticker_symbol }} value
              </template>
              <template #item.currency="{ item }">
                {{ item.currency }}
              </template>
              <template #item.amount="{ item }">
                {{ item.amount | formatPrice(floatingPrecision) }}
              </template>
              <template #item.usdValue="{ item }">
                {{
                  item.usdValue
                    | calculatePrice(exchangeRate(currency.ticker_symbol))
                    | formatPrice(floatingPrecision)
                }}
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
import { createNamespacedHelpers } from 'vuex';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { FiatBalance } from '@/model/blockchain-balances';

const { mapGetters, mapState } = createNamespacedHelpers('session');
const mapBalanceGetters = createNamespacedHelpers('balances').mapGetters;

@Component({
  computed: {
    ...mapGetters(['floatingPrecision']),
    ...mapBalanceGetters(['exchangeRate']),
    ...mapState(['currency'])
  }
})
export default class FiatBalances extends Vue {
  balance: string = '';
  selectedCurrency: string = '';
  currency!: Currency;

  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  errorTitle: string = '';
  errorMessage: string = '';

  fiatBalances: FiatBalance[] = [];

  get add(): boolean {
    return (
      this.fiatBalances.findIndex(
        value => value.currency === this.selectedCurrency
      ) === -1
    );
  }

  onChange() {
    const currency = this.selectedCurrency;
    let balance = Zero;
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
    { text: 'Currency', value: 'currency' },
    { text: 'Amount', value: 'amount' },
    { text: 'value', value: 'usdValue' }
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
          amount: bigNumberify(value[currency].amount as string),
          usdValue: bigNumberify(value[currency].usd_value as string)
        }));
      })
      .catch(reason => {
        console.log(`Error at querying fiat balances: ${reason}`);
      });
  }
}
</script>

<style scoped></style>
