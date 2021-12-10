<template>
  <data-table
    :headers="tableHeaders"
    :items="balances"
    :loading="loading"
    :loading-text="$t('asset_balances.loading')"
    :custom-sort="sortItems"
    sort-by="usdValue"
  >
    <template #header.usdValue>
      <div class="text-no-wrap">
        {{
          $t('asset_balances.headers.value', {
            currency
          })
        }}
      </div>
    </template>
    <template #header.usdPrice>
      <div class="text-no-wrap">
        {{
          $t('asset_balances.headers.price', {
            currency
          })
        }}
      </div>
    </template>
    <template #item.asset="{ item }">
      <asset-details opens-details :asset="item.asset" />
    </template>
    <template #item.usdPrice="{ item }">
      <amount-display
        v-if="item.usdPrice && item.usdPrice.gte(0)"
        tooltip
        show-currency="symbol"
        fiat-currency="USD"
        :price-asset="item.asset"
        :value="item.usdPrice"
      />
      <span v-else>-</span>
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
        <td colspan="3" v-text="$t('asset_balances.total')" />

        <td class="text-end">
          <amount-display
            fiat-currency="USD"
            show-currency="symbol"
            :value="total"
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
                :value="total"
              />
            </v-col>
          </v-row>
        </td>
      </tr>
    </template>
  </data-table>
</template>

<script lang="ts">
import { AssetBalanceWithPrice } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { IVueI18n } from 'vue-i18n';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import { setupAssetInfoRetrieval } from '@/composables/balances';
import { currency } from '@/composables/session';
import { balanceSum } from '@/filters';
import i18n from '@/i18n';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { getSortItems } from '@/utils/assets';

const tableHeaders = (i18n: IVueI18n) => {
  return [
    {
      text: i18n.t('asset_balances.headers.asset').toString(),
      value: 'asset',
      class: 'text-no-wrap',
      cellClass: 'asset-info'
    },
    {
      text: i18n.t('asset_balances.headers.price').toString(),
      value: 'usdPrice',
      align: 'end',
      class: 'text-no-wrap'
    },
    {
      text: i18n.t('asset_balances.headers.amount').toString(),
      value: 'amount',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'asset-divider'
    },
    {
      text: i18n.t('asset_balances.headers.value').toString(),
      value: 'usdValue',
      align: 'end',
      cellClass: 'user-asset-value',
      class: 'text-no-wrap'
    }
  ];
};

const AssetBalancesTable = defineComponent({
  name: 'AssetBalancesTable',
  components: { DataTable, AmountDisplay },
  props: {
    balances: {
      required: true,
      type: Array as PropType<AssetBalanceWithPrice[]>
    }
  },
  setup(props) {
    const { balances } = toRefs(props);
    const total = computed(() => {
      return balanceSum(balances.value.map(({ usdValue }) => usdValue));
    });

    const { isTaskRunning } = useTasks();
    const { getAssetInfo } = setupAssetInfoRetrieval();
    return {
      total,
      tableHeaders: tableHeaders(i18n),
      loading: isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES),
      sortItems: getSortItems(getAssetInfo),
      currency
    };
  }
});

export default AssetBalancesTable;
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

    &:hover {
      background-color: transparent !important;
    }
  }
}
</style>
