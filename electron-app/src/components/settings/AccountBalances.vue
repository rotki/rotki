<template>
  <div class="balance-table">
    <v-layout>
      <v-flex>
        <h3 class="text-center">{{ title }}</h3>
      </v-flex>
    </v-layout>
    <v-data-table :headers="headers" :items="balances">
      <template #header.usdValue>
        {{ currency.ticker_symbol }} value
      </template>
      <template #item.account="{ item }">
        {{ item.account }}
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
      <template v-if="items && items.length > 0" #body.append="{ items }">
        <tr class="balance-table__totals">
          <td>Totals</td>
          <td>
            {{
              items.map(val => val.amount)
                | balanceSum
                | formatPrice(floatingPrecision)
            }}
          </td>
          <td>
            {{
              items.map(val => val.usdValue)
                | balanceSum
                | calculatePrice(exchangeRate(currency.ticker_symbol))
                | formatPrice(floatingPrecision)
            }}
          </td>
        </tr>
      </template>
    </v-data-table>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { AccountBalance } from '@/model/blockchain-balances';
import { mapGetters, mapState } from 'vuex';
import { Currency } from '@/model/currency';

@Component({
  computed: {
    ...mapState(['currency']),
    ...mapGetters(['exchangeRate', 'floatingPrecision'])
  }
})
export default class AccountBalances extends Vue {
  @Prop({ required: true })
  balances!: AccountBalance[];
  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  title!: string;

  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  headers = [
    { text: 'Account', value: 'account' },
    { text: this.name, value: 'amount' },
    { text: 'USD Value', value: 'usdValue' }
  ];
}
</script>

<style scoped lang="scss">
.balance-table {
  margin-top: 16px;
  margin-bottom: 16px;
}

.balance-table__totals {
  font-weight: 500;
}
</style>
