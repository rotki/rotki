<template>
  <div class="asset-balances">
    <v-data-table
      :headers="headers"
      :items="balances"
      :loading="isLoading"
      :loading-text="$t('asset_balances.loading')"
      sort-by="usdValue"
      sort-desc
      :footer-props="footerProps"
    >
      <template #header.usdValue>
        {{
          $t('asset_balances.headers.value', {
            symbol
          })
        }}
      </template>
      <template #item.asset="{ item }">
        <asset-details :asset="item.asset" />
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display
          show-currency="symbol"
          :fiat-currency="item.asset"
          :amount="item.amount"
          :value="item.usdValue"
        />
      </template>
      <template v-if="balances.length > 0" #body.append>
        <tr class="asset-balances__total">
          <td v-text="$t('asset_balances.total')" />
          <td />
          <td class="text-end">
            <amount-display
              fiat-currency="USD"
              show-currency="symbol"
              :value="balances.map(val => val.usdValue) | balanceSum"
            />
          </td>
        </tr>
      </template>
    </v-data-table>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { footerProps } from '@/config/datatable.common';
import { CURRENCY_USD } from '@/data/currencies';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task-type';
import { AssetBalance } from '@/store/balances/types';

@Component({
  components: { AmountDisplay },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('session', ['floatingPrecision', 'currency']),
    ...mapGetters('balances', ['exchangeRate'])
  }
})
export default class AssetBalances extends Vue {
  @Prop({ required: true })
  balances!: AssetBalance[];
  @Prop({})
  title!: string;

  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
  isTaskRunning!: (type: TaskType) => boolean;

  get symbol(): string {
    return this.currency.ticker_symbol;
  }

  readonly footerProps = footerProps;

  get isLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  }

  readonly headers = [
    {
      text: this.$t('asset_balances.headers.asset').toString(),
      value: 'asset'
    },
    {
      text: this.$t('asset_balances.headers.amount').toString(),
      value: 'amount',
      align: 'end'
    },
    {
      text: this.$t('asset_balances.headers.value', {
        symbol: CURRENCY_USD
      }).toString(),
      value: 'usdValue',
      align: 'end'
    }
  ];
}
</script>

<style scoped lang="scss">
.asset-balances {
  margin-top: 16px;
  margin-bottom: 16px;

  &__balance {
    &__asset {
      display: flex;
      flex-direction: row;
      align-items: center;

      &__icon {
        margin-right: 8px;
      }
    }
  }

  &__total {
    font-weight: 500;
  }
}
</style>
