<template>
  <card outlined-body>
    <template #title>
      {{ tc('non_fungible_balances.title') }}
      <v-icon v-if="loading" color="primary" class="ml-2">
        mdi-spin mdi-loading
      </v-icon>
    </template>
    <template #details>
      <active-modules :modules="modules" class="mr-2" />
      <refresh-button
        :loading="loading"
        :tooltip="tc('non_fungible_balances.refresh')"
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
          :delete-tooltip="tc('non_fungible_balances.row.delete')"
          :edit-tooltip="tc('non_fungible_balances.row.edit')"
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
          :label="tc('common.total')"
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
      :title="tc('non_fungible_balances.delete.title')"
      :message="
        tc('non_fungible_balances.delete.message', 0, {
          asset: deleteAsset
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
import { useI18n } from 'vue-i18n-composable';
import { DataTableHeader } from 'vuetify';
import NonFungibleBalanceEdit from '@/components/accounts/balances/NonFungibleBalanceEdit.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAction from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { isSectionLoading } from '@/composables/common';
import { api } from '@/services/rotkehlchen-api';
import { useBalancesStore } from '@/store/balances';
import { NonFungibleBalance } from '@/store/balances/types';
import { Section } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module } from '@/types/modules';
import { assert } from '@/utils/assertions';
import { isVideo } from '@/utils/nft';

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
    const edit: Ref<NonFungibleBalance | null> = ref(null);
    const confirmDelete: Ref<NonFungibleBalance | null> = ref(null);

    const balancesStore = useBalancesStore();
    const { nfTotalValue, fetchNfBalances } = balancesStore;
    const { nfBalances } = storeToRefs(balancesStore);
    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
    const total = nfTotalValue();
    const { tc } = useI18n();
    const { notify } = useNotifications();

    const deleteAsset = computed(() => {
      const balance = get(confirmDelete);
      return !balance ? '' : balance.name ?? balance.id;
    });

    const mappedBalances = computed(() => {
      return get(nfBalances).map(balance => {
        return {
          ...balance,
          imageUrl: balance.imageUrl || '/assets/images/placeholder.svg',
          isVideo: isVideo(balance.imageUrl)
        };
      });
    });

    const tableHeaders = computed<DataTableHeader[]>(() => [
      {
        text: tc('common.name'),
        value: 'name',
        cellClass: 'text-no-wrap'
      },
      {
        text: tc('non_fungible_balance.column.price_in_asset'),
        value: 'priceInAsset',
        align: 'end',
        width: '75%',
        class: 'text-no-wrap'
      },
      {
        text: tc('common.price_in_symbol', 0, { symbol: get(currencySymbol) }),
        value: 'usdPrice',
        align: 'end',
        class: 'text-no-wrap'
      },
      {
        text: tc('non_fungible_balance.column.custom_price'),
        value: 'manuallyInput',
        class: 'text-no-wrap'
      },
      {
        text: tc('non_fungible_balance.column.actions'),
        value: 'actions',
        align: 'center',
        sortable: false,
        width: '50'
      }
    ]);

    const loading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);

    const setupRefresh = (ignoreCache: boolean = false) => {
      const payload = ignoreCache ? { ignoreCache: true } : undefined;

      return async () => await fetchNfBalances(payload);
    };

    const refresh = setupRefresh(true);
    const refreshBalances = setupRefresh();

    const setPrice = async (price: string, toAsset: string) => {
      const nft = get(edit);
      set(edit, null);
      assert(nft);
      try {
        await api.assets.setCurrentPrice(nft.id, toAsset, price);
        await refreshBalances();
      } catch (e: any) {
        notify({
          title: '',
          message: e.message,
          display: true
        });
      }
    };

    const deletePrice = async () => {
      const price = get(confirmDelete);
      assert(price);
      set(confirmDelete, null);
      try {
        await api.assets.deleteCurrentPrice(price.id);
        await refreshBalances();
      } catch (e: any) {
        notify({
          title: tc('non_fungible_balances.delete.error.title'),
          message: tc('non_fungible_balances.delete.error.message', 0, {
            asset: price.name ?? price.id
          }),
          display: true
        });
      }
    };

    return {
      edit,
      confirmDelete,
      loading,
      refresh,
      mappedBalances,
      currency: currencySymbol,
      tableHeaders,
      total,
      deleteAsset,
      setPrice,
      deletePrice,
      tc
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
