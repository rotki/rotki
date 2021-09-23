<template>
  <card outlined-body>
    <template #title>
      {{ $t('non_fungible_balances.title') }}
      <v-icon v-if="loading" color="primary" class="ml-2">
        mdi-spin mdi-loading
      </v-icon>
    </template>
    <data-table :headers="tableHeaders" :items="balances">
      <template #item.name="{ item }">
        {{ item.name ? item.name : item.id }}
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
          @delete-click="confirmId = item.id"
          @edit-click="edit = item"
        />
      </template>
      <template #item.hasPrice="{ item }">
        <v-icon v-if="item.hasPrice" color="green">mdi-check</v-icon>
      </template>
    </data-table>

    <non-fungible-balance-edit
      v-if="!!edit"
      :value="edit"
      @close="edit = null"
      @save="setPrice($event.price, $event.asset)"
    />
    <confirm-dialog
      :display="!!confirmId"
      :title="$t('non_fungible_balances.delete.title')"
      :message="$t('non_fungible_balances.delete.message', { confirmId })"
      @confirm="deletePrice"
      @cancel="confirmId = ''"
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
import { PricedNonFungibleBalance } from '@/components/accounts/balances/types';
import RowAction from '@/components/helper/RowActions.vue';
import { isSectionLoading } from '@/composables/common';
import i18n from '@/i18n';
import { AssetPriceArray } from '@/services/assets/types';
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
    value: 'hasPrice'
  },
  {
    text: i18n.t('non_fungible_balance.column.actions').toString(),
    align: 'center',
    value: 'actions'
  }
];

const setupEdit = (refresh: () => Promise<void>) => {
  const edit = ref<PricedNonFungibleBalance | null>(null);
  const setPrice = async (price: string, toAsset: string) => {
    const nft = edit.value;
    edit.value = null;
    assert(nft);
    try {
      await api.assets.setCurrentPrice(nft.id, toAsset, price);
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
  const confirmId = ref('');
  const deletePrice = async () => {
    const asset = confirmId.value;
    confirmId.value = '';
    try {
      await api.assets.deleteCurrentPrice(asset);
      await refresh();
    } catch (e: any) {
      await userNotify({
        title: i18n.t('non_fungible_balances.delete.error.title').toString(),
        message: i18n
          .t('non_fungible_balances.delete.error.message', { confirmId })
          .toString(),
        display: true
      });
    }
  };
  return {
    confirmId,
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
    error,
    prices
  };
};

export default defineComponent({
  name: 'NonFungibleBalances',
  components: { NonFungibleBalanceEdit, RowAction },
  setup() {
    const pricesRequest = requestPrices();
    const store = useStore();
    const balances = computed<PricedNonFungibleBalance[]>(() => {
      const prices = pricesRequest.prices.value;
      const balances: NonFungibleBalance[] =
        store.getters['balances/nfBalances'];
      const data: PricedNonFungibleBalance[] = [];

      for (const balance of balances) {
        const hasPrice = !!prices.find(({ asset }) => asset === balance.id);
        data.push({
          ...balance,
          hasPrice
        });
      }
      return data;
    });

    const refresh = async () => {
      return await store.dispatch(
        `balances/${BalanceActions.FETCH_NF_BALANCES}`
      );
    };

    return {
      loading: isSectionLoading(Section.NON_FUNGIBLE_BALANCES),
      ...pricesRequest,
      ...setupConfirm(refresh),
      ...setupEdit(refresh),
      balances,
      tableHeaders
    };
  }
});
</script>
