<template>
  <card outlined-body>
    <template #title>
      {{ $t('common.assets') }}
    </template>
    <template #subtitle>
      {{ $t('asset_table.subtitle') }}
    </template>
    <template #actions>
      <v-row>
        <v-col cols="12" md="4">
          <ignore-buttons
            :disabled="selected.length === 0"
            @ignore="massIgnore"
          />
          <div v-if="selected.length > 0" class="mt-2 ms-1">
            {{ $t('asset_table.selected', { count: selected.length }) }}
            <v-btn small text @click="selected = []">
              {{ $t('common.actions.clear_selection') }}
            </v-btn>
          </div>
        </v-col>
        <v-col />
        <v-col cols="12" md="auto">
          <v-checkbox
            v-model="onlyShowOwned"
            class="mt-0"
            :label="$t('asset_table.only_show_owned')"
            hide-details
          />
          <v-checkbox
            v-model="hideIgnoredAssets"
            class="mt-0"
            :label="$t('asset_table.hide_ignored_assets')"
            hide-details
          />
        </v-col>
        <v-col cols="12" md="4" class="pb-md-8">
          <v-text-field
            :value="pendingSearch"
            hide-details
            class="asset-table__filter"
            prepend-inner-icon="mdi-magnify"
            :label="$t('common.actions.filter')"
            outlined
            clearable
            @input="onSearchTermChange($event)"
          >
            <template v-if="isTimeoutPending" #append>
              <v-progress-circular
                indeterminate
                color="primary"
                width="2"
                size="24"
              />
            </template>
          </v-text-field>
        </v-col>
      </v-row>
    </template>
    <v-btn absolute fab top right dark color="primary" @click="add">
      <v-icon> mdi-plus </v-icon>
    </v-btn>
    <data-table
      v-model="selected"
      :items="filteredTokens"
      :loading="loading"
      :headers="tableHeaders"
      single-expand
      :expanded="expanded"
      item-key="identifier"
      sort-by="symbol"
      :sort-desc="false"
      :search="search"
      :single-select="false"
      show-select
      :custom-sort="sortItems"
      :custom-filter="assetFilter"
    >
      <template #item.symbol="{ item }">
        <asset-details-base
          :changeable="change"
          opens-details
          :asset="getAsset(item)"
        />
      </template>
      <template #item.address="{ item }">
        <hash-link v-if="item.address" :text="item.address" />
      </template>
      <template #item.started="{ item }">
        <date-display v-if="item.started" :timestamp="item.started" />
        <span v-else>-</span>
      </template>
      <template #item.assetType="{ item }">
        {{ formatType(item.assetType) }}
      </template>
      <template #item.ignored="{ item }">
        <div class="d-flex justify-center">
          <v-switch
            :input-value="isIgnored(item.identifier)"
            @change="toggleIgnoreAsset(item.identifier)"
          />
        </div>
      </template>
      <template #item.actions="{ item }">
        <row-actions
          :edit-tooltip="$t('asset_table.edit_tooltip')"
          :delete-tooltip="$t('asset_table.delete_tooltip')"
          @edit-click="edit(item)"
          @delete-click="deleteAsset(item)"
        >
          <copy-button
            class="mx-1"
            :tooltip="$t('asset_table.copy_identifier.tooltip')"
            :value="item.identifier"
          />
        </row-actions>
      </template>
      <template #expanded-item="{ item, headers }">
        <table-expand-container
          visible
          :colspan="headers.length"
          :padded="false"
        >
          <template #title>
            {{ $t('asset_table.underlying_tokens') }}
          </template>
          <v-simple-table>
            <thead>
              <tr>
                <th>{{ $t('common.address') }}</th>
                <th>{{ $t('underlying_token_manager.tokens.token_kind') }}</th>
                <th>{{ $t('underlying_token_manager.tokens.weight') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="token in item.underlyingTokens" :key="token.address">
                <td class="grow">
                  <hash-link :text="token.address" full-address />
                </td>
                <td class="shrink">{{ token.tokenKind.toUpperCase() }}</td>
                <td class="shrink">
                  {{
                    $t('underlying_token_manager.tokens.weight_percentage', {
                      weight: token.weight
                    })
                  }}
                </td>
              </tr>
            </tbody>
          </v-simple-table>
        </table-expand-container>
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="item.underlyingTokens && item.underlyingTokens.length > 0"
          :expanded="expanded.includes(item)"
          @click="expanded = expanded.includes(item) ? [] : [item]"
        />
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import { get, set, useTimeoutFn } from '@vueuse/core';
import { computed, defineComponent, PropType, Ref, ref, toRefs } from 'vue';
import { DataTableHeader } from 'vuetify';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import i18n from '@/i18n';
import { EthereumToken, ManagedAsset } from '@/services/assets/types';
import { useIgnoredAssetsStore } from '@/store/assets';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import { useMainStore } from '@/store/main';
import { ActionStatus } from '@/store/types';
import { Nullable } from '@/types';
import { compareAssets, getAddressFromEvmIdentifier } from '@/utils/assets';
import { uniqueStrings } from '@/utils/data';
import { toSentenceCase } from '@/utils/text';

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: i18n.t('common.asset').toString(),
    value: 'symbol'
  },
  {
    text: i18n.t('common.type').toString(),
    value: 'assetType'
  },
  {
    text: i18n.t('common.address').toString(),
    value: 'address'
  },
  {
    text: i18n.t('asset_table.headers.started').toString(),
    value: 'started'
  },
  {
    text: i18n.t('assets.ignore').toString(),
    value: 'ignored',
    align: 'center',
    sortable: false
  },
  {
    text: '',
    value: 'actions',
    sortable: false
  },
  {
    text: '',
    width: '48px',
    value: 'expand',
    sortable: false
  }
]);

export default defineComponent({
  name: 'AssetTable',
  components: {
    CopyButton,
    DataTable,
    TableExpandContainer,
    RowActions,
    RowExpander,
    AssetDetailsBase
  },
  props: {
    tokens: { required: true, type: Array as PropType<ManagedAsset[]> },
    loading: { required: false, type: Boolean, default: false },
    change: { required: true, type: Boolean }
  },
  emits: ['add', 'edit', 'delete-asset'],
  setup(props, { emit }) {
    const { tokens } = toRefs(props);
    const expanded = ref<ManagedAsset[]>([]);
    const search = ref<string>('');
    const pendingSearch = ref<string>('');
    const onlyShowOwned = ref<boolean>(false);
    const hideIgnoredAssets = ref<boolean>(false);

    const add = () => emit('add');
    const edit = (asset: ManagedAsset) => emit('edit', asset);
    const deleteAsset = (asset: ManagedAsset) => emit('delete-asset', asset);

    const { aggregatedAssets } = useBlockchainBalancesStore();

    const { isAssetIgnored, ignoreAsset, unignoreAsset } =
      useIgnoredAssetsStore();

    const isIgnored = (identifier: string) => {
      return isAssetIgnored(get(identifier));
    };

    const filteredTokens = computed<ManagedAsset[]>(() => {
      const showOwned = get(onlyShowOwned);
      const hideIgnored = get(hideIgnoredAssets);
      return get(tokens).filter(item => {
        return (
          (!showOwned ||
            get(aggregatedAssets(hideIgnored)).includes(item.identifier)) &&
          (!hideIgnored || !get(isIgnored(item.identifier)))
        );
      });
    });

    const {
      isPending: isTimeoutPending,
      start,
      stop
    } = useTimeoutFn(
      () => {
        set(search, get(pendingSearch));
      },
      600,
      { immediate: false }
    );

    const onSearchTermChange = (term: string) => {
      set(pendingSearch, term);
      if (get(isTimeoutPending)) {
        stop();
      }
      start();
    };

    const assetFilter = (
      value: Nullable<string>,
      search: Nullable<string>,
      item: Nullable<ManagedAsset>
    ) => {
      if (!search || !item) {
        return true;
      }

      const keyword = search?.toLocaleLowerCase()?.trim() ?? '';
      const name = item.name?.toLocaleLowerCase()?.trim() ?? '';
      const symbol = item.symbol?.toLocaleLowerCase()?.trim() ?? '';
      const address =
        (item as EthereumToken).address?.toLocaleLowerCase()?.trim() ?? '';
      return (
        symbol.indexOf(keyword) >= 0 ||
        name.indexOf(keyword) >= 0 ||
        address.indexOf(keyword) >= 0 ||
        item.identifier.indexOf(keyword) >= 0
      );
    };

    const sortItems = (
      items: ManagedAsset[],
      sortBy: (keyof ManagedAsset)[],
      sortDesc: boolean[]
    ): ManagedAsset[] => {
      const keyword = get(search)?.toLocaleLowerCase()?.trim() ?? '';
      return items.sort((a, b) =>
        compareAssets(a, b, sortBy[0], keyword, sortDesc[0])
      );
    };

    const formatType = (string?: string) => {
      return toSentenceCase(string ?? 'EVM token');
    };

    const getAsset = (item: EthereumToken) => {
      const name =
        item.name ??
        item.symbol ??
        getAddressFromEvmIdentifier(item.identifier);
      return {
        name,
        symbol: item.symbol ?? '',
        identifier: item.identifier
      };
    };

    const toggleIgnoreAsset = (identifier: string) => {
      if (get(isIgnored(identifier))) {
        unignoreAsset(get(identifier));
      } else {
        ignoreAsset(get(identifier));
      }
    };

    const selected: Ref<ManagedAsset[]> = ref([]);

    const { setMessage } = useMainStore();
    const massIgnore = async (ignored: boolean) => {
      const ids = get(selected)
        .filter(item => {
          const isItemIgnored = get(isIgnored(item.identifier));
          return ignored ? !isItemIgnored : isItemIgnored;
        })
        .map(item => item.identifier)
        .filter(uniqueStrings);

      let status: ActionStatus;

      if (ids.length === 0) {
        const choice = ignored ? 1 : 2;
        setMessage({
          success: false,
          title: i18n.tc('ignore.no_items.title', choice),
          description: i18n.tc('ignore.no_items.description', choice)
        });
        return;
      }

      if (ignored) {
        status = await ignoreAsset(ids);
      } else {
        status = await unignoreAsset(ids);
      }

      if (status.success) {
        set(selected, []);
      }
    };

    return {
      selected,
      filteredTokens,
      pendingSearch,
      onSearchTermChange,
      isTimeoutPending,
      add,
      edit,
      deleteAsset,
      tableHeaders,
      expanded,
      search,
      sortItems,
      assetFilter,
      getAsset,
      formatType,
      onlyShowOwned,
      hideIgnoredAssets,
      isIgnored,
      toggleIgnoreAsset,
      massIgnore
    };
  }
});
</script>
