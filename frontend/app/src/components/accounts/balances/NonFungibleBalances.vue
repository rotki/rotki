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
        <div class="d-flex align-center">
          <div class="my-2 non-fungible-balances__item__preview">
            <video
              v-if="item.isVideo"
              width="100%"
              height="100%"
              aspect-ratio="1"
              :src="item.imageUrl"
            />
            <v-img
              v-if="!item.isVideo"
              :src="item.imageUrl"
              width="100%"
              height="100%"
              contain
              aspect-ratio="1"
            />
          </div>
          <span class="ml-4">
            {{ item.name ? item.name : item.id }}
          </span>
        </div>
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
          :label="$t('non_fungible_balances.row.total')"
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
import { DataTableHeader } from 'vuetify';
import NonFungibleBalanceEdit from '@/components/accounts/balances/NonFungibleBalanceEdit.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAction from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { isSectionLoading } from '@/composables/common';
import { setupGeneralSettings } from '@/composables/session';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { BalanceActions } from '@/store/balances/action-types';
import { NonFungibleBalance } from '@/store/balances/types';
import { Section } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import { useStore } from '@/store/utils';
import { Module } from '@/types/modules';
import { assert } from '@/utils/assertions';
import { Zero } from '@/utils/bignumbers';
import { isVideo } from '@/utils/nft';

const tableHeaders = (currency: Ref<string>) => {
  return computed<DataTableHeader[]>(() => {
    return [
      {
        text: i18n.t('non_fungible_balance.column.name').toString(),
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
          .t('non_fungible_balance.column.price', { currency: get(currency) })
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
    const store = useStore();
    const balances = computed<NonFungibleBalance[]>(() => {
      return store.getters['balances/nfBalances'];
    });

    const { currencySymbol } = setupGeneralSettings();

    const setupRefresh = (ignoreCache: boolean = false) => {
      const payload = ignoreCache ? { ignoreCache: true } : undefined;
      return async () =>
        await store.dispatch(
          `balances/${BalanceActions.FETCH_NF_BALANCES}`,
          payload
        );
    };

    const refresh = setupRefresh(true);
    const refreshBalances = setupRefresh();

    const total = computed(() => {
      return get(balances).reduce(
        (sum, value) => sum.plus(value.usdPrice),
        Zero
      );
    });

    const mappedBalances = computed(() => {
      return get(balances).map(balance => {
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
