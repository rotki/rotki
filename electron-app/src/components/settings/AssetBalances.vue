<template>
  <div class="asset-balances">
    <v-row v-if="title">
      <v-col>
        <h3 class="text-center">{{ title }}</h3>
      </v-col>
    </v-row>
    <v-data-table
      :headers="headers"
      :items="balances"
      :loading="isLoading"
      loading-text="Please wait while Rotki queries the blockchain..."
      sort-by="usdValue"
      sort-desc
    >
      <template #header.usdValue> {{ currency.ticker_symbol }} value </template>
      <template #item.asset="{ item }">
        <span class="asset-balances__balance__asset">
          <crypto-icon
            width="26px"
            class="asset-balances__balance__asset__icon"
            :symbol="item.asset"
          ></crypto-icon>
          {{ item.asset }}
        </span>
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount"></amount-display>
      </template>
      <template #item.usdValue="{ item }">
        <amount-display fiat :value="item.usdValue"></amount-display>
      </template>
      <template v-if="balances.length > 0" #body.append>
        <tr class="asset-balances__total">
          <td>Total</td>
          <td></td>
          <td class="text-end">
            <amount-display
              usd-value
              :value="balances.map(val => val.usdValue) | balanceSum"
            >
            </amount-display>
          </td>
        </tr>
      </template>
    </v-data-table>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { AssetBalance } from '@/model/blockchain-balances';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task';

const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');
const { mapGetters } = createNamespacedHelpers('session');
const { mapGetters: mapBalancesGetters } = createNamespacedHelpers('balances');

@Component({
  components: { AmountDisplay, CryptoIcon },
  computed: {
    ...mapTaskGetters(['isTaskRunning']),
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapBalancesGetters(['exchangeRate'])
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

  get isLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  }

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Amount', value: 'amount', align: 'end' },
    { text: 'USD Value', value: 'usdValue', align: 'end' }
  ];
}
</script>

<style scoped lang="scss">
.asset-balances {
  margin-top: 16px;
  margin-bottom: 16px;
}

.asset-balances__balance__asset {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.asset-balances__balance__asset__icon {
  margin-right: 8px;
}

.asset-balances__total {
  font-weight: 500;
}
</style>
