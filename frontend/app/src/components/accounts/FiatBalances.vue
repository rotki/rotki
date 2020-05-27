<template>
  <v-row class="fiat-balances">
    <v-col>
      <v-card>
        <v-card-title>
          Fiat Balances
          <v-tooltip bottom style="z-index: 200;">
            <template #activator="{ on }">
              <v-icon
                small
                class="mb-3 ml-1 summary-card__header__tooltip"
                v-on="on"
              >
                fa fa-info-circle
              </v-icon>
            </template>
            <div>
              When aggregating, fiat balances will be<br />
              reported together with Manual Balances<br />
              with a location of "banks".
            </div>
          </v-tooltip>
        </v-card-title>
        <v-card-text>
          <v-select
            v-model="selectedCurrency"
            class="fiat-balances__currency"
            item-value="ticker_symbol"
            item-text="ticker_symbol"
            :items="availableCurrencies"
            label="Currency"
            @change="onChange()"
          ></v-select>
          <v-text-field
            v-model="balance"
            class="fiat-balances__balance"
            type="number"
            label="Balance"
            prepend-icon="fa-money"
          ></v-text-field>
          <v-btn
            class="fiat-balances__action-button"
            color="primary"
            depressed
            :disabled="!selectedCurrency"
            @click="modify()"
          >
            {{ add ? 'Add Balance' : 'Modify Balance' }}
          </v-btn>
          <v-col cols="12">
            <v-data-table
              :headers="headers"
              :items="fiatBalances"
              sort-by="usdValue"
              sort-desc
            >
              <template #header.usdValue>
                {{ currency.ticker_symbol }} value
              </template>
              <template #item.currency="{ item }">
                {{ item.currency }}
              </template>
              <template #item.amount="{ item }">
                <amount-display :value="item.amount"></amount-display>
              </template>
              <template #item.usdValue="{ item }">
                <amount-display
                  :fiat-currency="item.currency"
                  :amount="item.amount"
                  :value="item.usdValue"
                ></amount-display>
              </template>
              <template v-if="fiatBalances.length > 0" #body.append>
                <tr class="fiat-balances__total">
                  <td>Total</td>
                  <td></td>
                  <td class="text-end">
                    <amount-display
                      fiat-currency="USD"
                      :value="
                        fiatBalances.map(val => val.usdValue) | balanceSum
                      "
                    ></amount-display>
                  </td>
                </tr>
              </template>
            </v-data-table>
          </v-col>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { currencies } from '@/data/currencies';
import { FiatBalance } from '@/model/blockchain-balances';
import { Currency } from '@/model/currency';
import { Message } from '@/store/store';
import { Zero } from '@/utils/bignumbers';

const { mapGetters } = createNamespacedHelpers('session');
const {
  mapGetters: mapBalanceGetters,
  mapState: mapBalanceState
} = createNamespacedHelpers('balances');

@Component({
  components: { AmountDisplay },
  computed: {
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapBalanceGetters(['exchangeRate']),
    ...mapBalanceState(['fiatBalances'])
  }
})
export default class FiatBalances extends Vue {
  balance: string = '';
  selectedCurrency: string = '';
  currency!: Currency;

  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  fiatBalances!: FiatBalance[];

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
    { text: 'Amount', value: 'amount', align: 'end' },
    { text: 'value', value: 'usdValue', align: 'end' }
  ];

  get availableCurrencies(): Currency[] {
    return currencies;
  }

  modify() {
    const { commit, dispatch } = this.$store;

    const currency = this.selectedCurrency;
    const balance = this.balance;
    this.$api
      .setFiatBalance(currency, balance.toString())
      .then(() => {
        dispatch('balances/fetchFiatBalances');
        this.selectedCurrency = '';
        this.balance = '';
      })
      .catch((reason: Error) => {
        commit('setMessage', {
          title: 'Balance Modification Error',
          description: `Error at modifying ${currency} balance: ${reason.message}`
        } as Message);
      });
  }
}
</script>

<style scoped lang="scss">
.fiat-balances {
  &__total {
    font-weight: 500;
  }
}
</style>
