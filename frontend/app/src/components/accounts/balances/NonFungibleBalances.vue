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
import { computed, defineComponent, ref } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import NonFungibleBalanceEdit from '@/components/accounts/balances/NonFungibleBalanceEdit.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAction from '@/components/helper/RowActions.vue';
import { isSectionLoading } from '@/composables/common';
import i18n from '@/i18n';
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
  const edit = ref<NonFungibleBalance | null>(null);
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
  const confirmDelete = ref<NonFungibleBalance | null>(null);
  const deletePrice = async () => {
    const price = confirmDelete.value;
    assert(price);
    confirmDelete.value = null;
    try {
      await api.assets.deleteCurrentPrice(price.id);
      await refresh();
    } catch (e: any) {
      await userNotify({
        title: i18n.t('non_fungible_balances.delete.error.title').toString(),
        message: i18n
          .t('non_fungible_balances.delete.error.message', {
            asset: price.name ?? price.id
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

export default defineComponent({
  name: 'NonFungibleBalances',
  components: { RefreshButton, NonFungibleBalanceEdit, RowAction },
  setup() {
    const store = useStore();
    const balances = computed<NonFungibleBalance[]>(() => {
      return store.getters['balances/nfBalances'];
    });

    const refresh = async () => {
      return await store.dispatch(
        `balances/${BalanceActions.FETCH_NF_BALANCES}`
      );
    };

    return {
      loading: isSectionLoading(Section.NON_FUNGIBLE_BALANCES),
      ...setupConfirm(refresh),
      ...setupEdit(refresh),
      refresh,
      balances,
      tableHeaders,
      getAsset: (price: NonFungibleBalance | null) => {
        if (!price) {
          return '';
        }

        return price.name ?? price.id;
      }
    };
  }
});
</script>
