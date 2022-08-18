<template>
  <card outlined-body>
    <template #title>
      {{ $t('non_fungible_balances.title') }}
      <v-icon v-if="loading" color="primary" class="ml-2">
        mdi-spin mdi-loading
      </v-icon>
    </template>
    <template #details>
      <active-modules :modules="modules" class="mr-2" />
      <refresh-button
        :loading="loading"
        :tooltip="$t('non_fungible_balances.refresh')"
        @refresh="refresh"
      />
    </template>
    <data-table
      :headers="tableHeaders"
      :items="mappedBalances"
      sort-by="usdPrice"
    >
      <template #item.name="{ item }">
        <nft-details :identifier="item.id" />
      </template>
      <template #item.usdPrice="{ item }">
        <amount-display
          :value="item.usdPrice"
          show-currency="symbol"
          fiat-currency="USD"
        />
      </template>
      <template #item.priceInAsset="{ item }">
        <amount-display
          v-if="item.priceAsset !== currency"
          :value="item.priceInAsset"
          :asset="item.priceAsset"
        />
        <span v-else>-</span>
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
      <template #body.append="{ isMobile }">
        <row-append
          label-colspan="2"
          :label="$t('common.total')"
          :right-patch-colspan="1"
          :is-mobile="isMobile"
        >
          <amount-display
            :value="total"
            show-currency="symbol"
            fiat-currency="USD"
          />
        </row-append>
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
  PropType,
  Ref,
  ref
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import NonFungibleBalanceEdit from '@/components/accounts/balances/NonFungibleBalanceEdit.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAction from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { isSectionLoading } from '@/composables/common';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useBalancesStore } from '@/store/balances';
import { NonFungibleBalance } from '@/store/balances/types';
import { Section } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module } from '@/types/modules';
import { assert } from '@/utils/assertions';
import { isVideo } from '@/utils/nft';

const tableHeaders = (symbol: Ref<string>) => {
  return computed<DataTableHeader[]>(() => {
    return [
      {
        text: i18n.t('common.name').toString(),
        value: 'name',
        cellClass: 'text-no-wrap'
      },
      {
        text: i18n.t('non_fungible_balance.column.price_in_asset').toString(),
        value: 'priceInAsset',
        align: 'end',
        width: '75%',
        class: 'text-no-wrap'
      },
      {
        text: i18n
          .t('common.price_in_symbol', { symbol: get(symbol) })
          .toString(),
        value: 'usdPrice',
        align: 'end',
        class: 'text-no-wrap'
      },
      {
        text: i18n.t('non_fungible_balance.column.custom_price').toString(),
        value: 'manuallyInput',
        class: 'text-no-wrap'
      },
      {
        text: i18n.t('non_fungible_balance.column.actions').toString(),
        value: 'actions',
        align: 'center',
        sortable: false,
        width: '50'
      }
    ];
  });
};

const setupEdit = (refresh: () => Promise<void>) => {
  const edit = ref<NonFungibleBalance | null>(null);
  const setPrice = async (price: string, toAsset: string) => {
    const nft = get(edit);
    set(edit, null);
    assert(nft);
    try {
      await api.assets.setCurrentPrice(nft.id, toAsset, price);
      await refresh();
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
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
    const price = get(confirmDelete);
    assert(price);
    set(confirmDelete, null);
    try {
      await api.assets.deleteCurrentPrice(price.id);
      await refresh();
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
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
  components: {
    NftDetails,
    RowAppend,
    ActiveModules,
    RefreshButton,
    NonFungibleBalanceEdit,
    RowAction
  },
  props: {
    modules: {
      required: true,
      type: Array as PropType<Module[]>
    }
  },
  setup() {
    const balancesStore = useBalancesStore();
    const { nfTotalValue, fetchNfBalances } = balancesStore;
    const { nfBalances } = storeToRefs(balancesStore);

    const total = nfTotalValue();

    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

    const setupRefresh = (ignoreCache: boolean = false) => {
      const payload = ignoreCache ? { ignoreCache: true } : undefined;

      return async () => await fetchNfBalances(payload);
    };

    const refresh = setupRefresh(true);
    const refreshBalances = setupRefresh();

    const mappedBalances = computed(() => {
      return get(nfBalances).map(balance => {
        return {
          ...balance,
          imageUrl: balance.imageUrl || '/assets/images/placeholder.svg',
          isVideo: isVideo(balance.imageUrl)
        };
      });
    });

    return {
      loading: isSectionLoading(Section.NON_FUNGIBLE_BALANCES),
      ...setupConfirm(refreshBalances),
      ...setupEdit(refreshBalances),
      refresh,
      mappedBalances,
      currency: currencySymbol,
      tableHeaders: tableHeaders(currencySymbol),
      total,
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
<style scoped lang="scss">
.non-fungible-balances {
  &__item {
    &__preview {
      width: 50px;
      height: 50px;
      max-width: 50px;
    }
  }
}
</style>
