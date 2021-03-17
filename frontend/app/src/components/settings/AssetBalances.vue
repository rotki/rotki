<template>
  <v-sheet class="asset-balances" :rounded="!flat" :outlined="!flat">
    <data-table
      :headers="headers"
      :items="balances"
      :loading="isLoading"
      :loading-text="$t('asset_balances.loading')"
      sort-by="usdValue"
    >
      <template #header.usdValue>
        <div class="text-no-wrap">
          {{
            $t('asset_balances.headers.value', {
              symbol
            })
          }}
        </div>
      </template>
      <template #header.price>
        <div class="text-no-wrap">
          {{
            $t('asset_balances.headers.price', {
              symbol
            })
          }}
        </div>
      </template>
      <template #item.asset="{ item }">
        <asset-details opens-details :asset="item.asset" />
      </template>
      <template #item.price="{ item }">
        <amount-display
          tooltip
          show-currency="symbol"
          fiat-currency="USD"
          :price-asset="item.asset"
          :value="prices[item.asset] ? prices[item.asset] : '-'"
        />
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
        <tr v-if="$vuetify.breakpoint.smAndUp" class="asset-balances__total">
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
        <tr v-else>
          <td>
            <v-row justify="space-between">
              <v-col cols="auto" class="font-weight-medium">
                {{ $t('asset_balances.total') }}
              </v-col>
              <v-col cols="auto">
                <amount-display
                  fiat-currency="USD"
                  show-currency="symbol"
                  :value="balances.map(val => val.usdValue) | balanceSum"
                />
              </v-col>
            </v-row>
          </td>
        </tr>
      </template>
    </data-table>
  </v-sheet>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters, mapState } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import { CURRENCY_USD } from '@/data/currencies';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task-type';
import { AssetBalance, AssetPrices } from '@/store/balances/types';

@Component({
  components: { DataTable, AmountDisplay },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('session', ['floatingPrecision', 'currency']),
    ...mapGetters('balances', ['exchangeRate']),
    ...mapState('balances', ['prices'])
  }
})
export default class AssetBalances extends Vue {
  @Prop({ required: true })
  balances!: AssetBalance[];
  @Prop({})
  title!: string;
  @Prop({ required: false, default: false, type: Boolean })
  flat!: boolean;

  currency!: Currency;
  floatingPrecision!: number;
  prices!: AssetPrices;
  exchangeRate!: (currency: string) => number;
  isTaskRunning!: (type: TaskType) => boolean;

  get symbol(): string {
    return this.currency.ticker_symbol;
  }

  get isLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  }

  get headers(): DataTableHeader[] {
    return [
      {
        text: this.$t('asset_balances.headers.asset').toString(),
        value: 'asset',
        class: 'text-no-wrap',
        cellClass: 'asset-info'
      },
      {
        text: this.$t('asset_balances.headers.price', {
          symbol: this.symbol ?? CURRENCY_USD
        }).toString(),
        value: 'price',
        align: 'end',
        class: 'text-no-wrap'
      },
      {
        text: this.$t('asset_balances.headers.amount').toString(),
        value: 'amount',
        align: 'end',
        class: 'text-no-wrap',
        cellClass: 'asset-divider'
      },
      {
        text: this.$t('asset_balances.headers.value', {
          symbol: this.symbol ?? CURRENCY_USD
        }).toString(),
        value: 'usdValue',
        align: 'end',
        cellClass: 'user-asset-value',
        class: 'text-no-wrap'
      }
    ];
  }
}
</script>

<style scoped lang="scss">
::v-deep {
  .asset-divider {
    width: 100%;

    @media (min-width: 2000px) {
      width: 50%;
    }
  }

  .asset-info {
    @media (min-width: 2000px) {
      width: 200px;
    }
  }
}

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
