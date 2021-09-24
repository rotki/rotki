<template>
  <card outlined-body>
    <template #title>
      {{ $t('non_fungible_balances.title') }}
      <v-icon v-if="loading" color="primary" class="ml-2">
        mdi-spin mdi-loading
      </v-icon>
    </template>
    <template #details>
      <refresh-button
        :loading="loading"
        :tooltip="$t('non_fungible_balances.refresh')"
        @refresh="refresh"
      />
    </template>
    <data-table :headers="tableHeaders" :items="balances" sort-by="usdPrice">
      <template #item.name="{ item }">
        {{ item.name ? item.name : item.asset }}
      </template>
      <template #item.usdPrice="{ item }">
        <amount-display
          :value="item.usdPrice"
          show-currency="symbol"
          fiat-currency="USD"
        />
      </template>
      <template #item.actions="{ item }">
        <row-action
          :delete-tooltip="$t('non_fungible_balances.row.delete')"
          :edit-tooltip="$t('non_fungible_balances.row.edit')"
          :delete-disabled="!item.manuallyInput"
          @delete-click="confirmDelete = item"
          @edit-click="edit = item"
        />
      </template>
      <template #item.manuallyInput="{ item }">
        <v-icon v-if="item.manuallyInput" color="green">mdi-check</v-icon>
      </template>
    </data-table>

    <non-fungible-balance-edit
      v-if="!!edit"
      :value="edit"
      @close="edit = null"
      @save="setPrice($event.price, $event.asset)"
    />
    <confirm-dialog
      :display="!!confirmDelete"
      :title="$t('non_fungible_balances.delete.title')"
      :message="
        $t('non_fungible_balances.delete.message', {
          asset: getAsset(confirmDelete)
        })
      "
      @confirm="deletePrice"
      @cancel="confirmDelete = null"
    />
  </card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  ref
} from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import NonFungibleBalanceEdit from '@/components/accounts/balances/NonFungibleBalanceEdit.vue';
import { NonFungiblePrice } from '@/components/accounts/balances/types';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAction from '@/components/helper/RowActions.vue';
import { isSectionLoading } from '@/composables/common';
import i18n from '@/i18n';
import { AssetPrice, AssetPriceArray } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { BalanceActions } from '@/store/balances/action-types';
import { NonFungibleBalance } from '@/store/balances/types';
import { Section } from '@/store/const';
import { userNotify } from '@/store/notifications/utils';
import { useStore } from '@/store/utils';
import { assert } from '@/utils/assertions';

const tableHeaders: DataTableHeader[] = [
  {
    text: i18n.t('non_fungible_balance.column.name').toString(),
    value: 'name',
    cellClass: 'text-no-wrap'
  },
  {
    text: i18n.t('non_fungible_balance.column.price').toString(),
    value: 'usdPrice',
    align: 'end',
    width: '75%'
  },
  {
    text: i18n.t('non_fungible_balance.column.custom_price').toString(),
    value: 'manuallyInput'
  },
  {
    text: i18n.t('non_fungible_balance.column.actions').toString(),
    align: 'center',
    value: 'actions'
  }
];

const setupEdit = (refresh: () => Promise<void>) => {
  const edit = ref<NonFungiblePrice | null>(null);
  const setPrice = async (price: string, toAsset: string) => {
    const nft = edit.value;
    edit.value = null;
    assert(nft);
    try {
      await api.assets.setCurrentPrice(nft.asset, toAsset, price);
      await refresh();
    } catch (e: any) {
      await userNotify({
        title: '',
        message: e.message,
        display: true
      });
    }
  };

  return {
    edit,
    setPrice
  };
};

const setupConfirm = (refresh: () => Promise<void>) => {
  const confirmDelete = ref<NonFungiblePrice | null>(null);
  const deletePrice = async () => {
    const price = confirmDelete.value;
    assert(price);
    confirmDelete.value = null;
    try {
      await api.assets.deleteCurrentPrice(price.asset);
      await refresh();
    } catch (e: any) {
      await userNotify({
        title: i18n.t('non_fungible_balances.delete.error.title').toString(),
        message: i18n
          .t('non_fungible_balances.delete.error.message', {
            asset: price.name ?? price.asset
          })
          .toString(),
        display: true
      });
    }
  };
  return {
    confirmDelete,
    deletePrice
  };
};

const requestPrices = () => {
  const prices = ref<AssetPriceArray>([]);
  const error = ref('');
  const fetchPrices = async () => {
    try {
      const data = await api.assets.fetchCurrentPrices();
      prices.value = AssetPriceArray.parse(data);
    } catch (e: any) {
      error.value = e.message;
    }
  };
  onMounted(fetchPrices);
  return {
    fetchPrices,
    error,
    prices
  };
};

export default defineComponent({
  name: 'NonFungibleBalances',
  components: { RefreshButton, NonFungibleBalanceEdit, RowAction },
  setup() {
    const pricesRequest = requestPrices();
    const store = useStore();
    const balances = computed<NonFungiblePrice[]>(() => {
      const prices = pricesRequest.prices.value;
      const balances: NonFungibleBalance[] =
        store.getters['balances/nfBalances'];
      const data: NonFungiblePrice[] = [];

      for (const balance of balances) {
        const price = prices.find(({ asset }) => asset === balance.id);
        let entry: NonFungiblePrice;
        if (!price) {
          entry = {
            name: balance.name,
            asset: balance.id,
            manuallyInput: false,
            priceAsset: 'USD',
            priceInAsset: balance.usdPrice,
            usdPrice: balance.usdPrice
          };
        } else {
          entry = {
            ...(price as AssetPrice),
            name: balance.name
          };
        }

        data.push(entry);
      }
      return data;
    });

    const refresh = async () => {
      await pricesRequest.fetchPrices();
      return await store.dispatch(
        `balances/${BalanceActions.FETCH_NF_BALANCES}`
      );
    };

    return {
      loading: isSectionLoading(Section.NON_FUNGIBLE_BALANCES),
      ...pricesRequest,
      ...setupConfirm(refresh),
      ...setupEdit(refresh),
      refresh,
      balances,
      tableHeaders,
      getAsset: (price: NonFungiblePrice | null) => {
        if (!price) {
          return '';
        }

        return price.name ?? price.asset;
      }
    };
  }
});
</script>
