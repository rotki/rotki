<script setup lang="ts">
import { type SupportedAsset } from '@rotki/common/lib/data';
import { type DataTableHeader } from 'vuetify';
import { type TablePagination } from '@/types/pagination';
import { type Filters, type Matcher } from '@/composables/filters/assets';
import {
  type AssetRequestPayload,
  CUSTOM_ASSET,
  type IgnoredAssetsHandlingType
} from '@/types/asset';
import { type ActionStatus } from '@/types/action';

const props = withDefaults(
  defineProps<{
    tokens: SupportedAsset[];
    serverItemLength: number;
    matchers: Matcher[];
    filters: Filters;
    expanded: SupportedAsset[];
    selected: SupportedAsset[];
    options: TablePagination<SupportedAsset>;
    ignoredAssets: string[];
    onlyShowOwned: boolean;
    ignoredAssetsHandling: IgnoredAssetsHandlingType;
    loading?: boolean;
  }>(),
  { loading: false }
);

const emit = defineEmits<{
  (e: 'add'): void;
  (e: 'refresh'): void;
  (e: 'edit', asset: SupportedAsset): void;
  (e: 'delete-asset', asset: SupportedAsset): void;
  (e: 'update:pagination', pagination: AssetRequestPayload): void;
  (e: 'update:filters', filters: Filters): void;
  (e: 'update:selected', selectedAssets: SupportedAsset[]): void;
  (e: 'update:expanded', expandedAssets: SupportedAsset[]): void;
  (
    e: 'update:ignored-assets-handling',
    ignoredAssetsHandling: IgnoredAssetsHandlingType
  ): void;
  (e: 'update:only-show-owned', onlyShowOwned: boolean): void;
}>();

const { t } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.asset'),
    value: 'symbol'
  },
  {
    text: t('common.type'),
    value: 'type'
  },
  {
    text: t('common.address'),
    value: 'address'
  },
  {
    text: t('asset_table.headers.started'),
    value: 'started'
  },
  {
    text: t('assets.ignore'),
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

const add = () => emit('add');
const edit = (asset: SupportedAsset) => emit('edit', asset);
const deleteAsset = (asset: SupportedAsset) => emit('delete-asset', asset);

const updatePagination = (pagination: AssetRequestPayload) =>
  emit('update:pagination', pagination);
const updateFilter = (filters: Filters) => emit('update:filters', filters);
const updateSelected = (selectedAssets: SupportedAsset[]) =>
  emit('update:selected', selectedAssets);
const updateExpanded = (expandedAssets: SupportedAsset[]) =>
  emit('update:expanded', expandedAssets);
const updateIgnoredAssetsHandling = (
  ignoredAssetsHandling: IgnoredAssetsHandlingType
) => {
  emit('update:ignored-assets-handling', ignoredAssetsHandling);
};
const updateShowOwned = (onlyShowOwned: boolean) => {
  emit('update:only-show-owned', onlyShowOwned);
};

const formatType = (string?: string) => toSentenceCase(string ?? 'EVM token');

const getAsset = (item: SupportedAsset) => {
  const name =
    item.name ??
    item.symbol ??
    (isEvmIdentifier(item.identifier)
      ? getAddressFromEvmIdentifier(item.identifier)
      : item.identifier);

  return {
    name,
    symbol: item.symbol ?? '',
    identifier: item.identifier,
    isCustomAsset: item.assetType === CUSTOM_ASSET,
    customAssetType: item.customAssetType ?? ''
  };
};

const { setMessage } = useMessageStore();
const { isAssetIgnored, ignoreAsset, unignoreAsset } = useIgnoredAssetsStore();
const { getChain } = useSupportedChains();
const css = useCssModule();

const toggleIgnoreAsset = async (identifier: string) => {
  if (get(isAssetIgnored(identifier))) {
    await unignoreAsset(identifier);
  } else {
    await ignoreAsset(identifier);
  }
  if (props.ignoredAssetsHandling !== 'none') {
    emit('refresh');
  }
};

const massIgnore = async (ignored: boolean) => {
  const ids = get(props.selected)
    .filter(item => {
      const isItemIgnored = get(isAssetIgnored(item.identifier));
      return ignored ? !isItemIgnored : isItemIgnored;
    })
    .map(item => item.identifier)
    .filter(uniqueStrings);

  let status: ActionStatus;

  if (ids.length === 0) {
    const choice = ignored ? 1 : 2;
    setMessage({
      success: false,
      title: t('ignore.no_items.title', choice),
      description: t('ignore.no_items.description', choice)
    });
    return;
  }

  if (ignored) {
    status = await ignoreAsset(ids);
  } else {
    status = await unignoreAsset(ids);
  }

  if (status.success) {
    updateSelected([]);
    if (props.ignoredAssetsHandling !== 'none') {
      emit('refresh');
    }
  }
};
</script>

<template>
  <card outlined-body data-cy="managed-assets-table">
    <template #title>
      {{ t('common.assets') }}
    </template>
    <template #subtitle>
      {{ t('asset_table.managed.subtitle') }}
    </template>
    <template #actions>
      <v-row>
        <v-col cols="12" md="4">
          <ignore-buttons
            :disabled="selected.length === 0"
            @ignore="massIgnore($event)"
          />
          <div v-if="selected.length > 0" class="mt-2 ms-1">
            {{ t('asset_table.selected', { count: selected.length }) }}
            <v-btn small text @click="updateSelected([])">
              {{ t('common.actions.clear_selection') }}
            </v-btn>
          </div>
        </v-col>
        <v-col />
        <v-col cols="12" md="auto">
          <v-menu offset-y :close-on-content-click="false">
            <template #activator="{ on }">
              <v-btn
                outlined
                text
                height="40px"
                data-cy="asset-filter"
                v-on="on"
              >
                {{ t('common.actions.filter') }}
                <v-icon class="ml-2">mdi-chevron-down</v-icon>
              </v-btn>
            </template>
            <v-list data-cy="asset-filter-menu">
              <v-list-item link @click="updateShowOwned(!onlyShowOwned)">
                <v-checkbox
                  data-cy="asset-filter-only-show-owned"
                  :input-value="onlyShowOwned"
                  class="mt-0 py-2"
                  :label="t('asset_table.only_show_owned')"
                  hide-details
                />
              </v-list-item>
              <v-list-item
                :class="css['filter-heading']"
                class="font-weight-bold text-uppercase py-2"
              >
                {{ t('asset_table.filter_by_ignored_status') }}
              </v-list-item>
              <v-list-item>
                <v-radio-group
                  :value="ignoredAssetsHandling"
                  class="mt-0"
                  data-cy="asset-filter-ignored"
                  @change="updateIgnoredAssetsHandling($event)"
                >
                  <v-radio value="none" :label="t('asset_table.show_all')" />
                  <v-radio
                    value="exclude"
                    :label="t('asset_table.only_show_unignored')"
                  />
                  <v-radio
                    value="show_only"
                    :label="
                      t(
                        'asset_table.only_show_ignored',
                        {
                          length: ignoredAssets.length
                        },
                        1
                      )
                    "
                  />
                </v-radio-group>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-col>
        <v-col cols="12" md="4" class="pb-md-8">
          <table-filter
            :matches="filters"
            :matchers="matchers"
            @update:matches="updateFilter($event)"
          />
        </v-col>
      </v-row>
    </template>
    <v-btn
      data-cy="managed-asset-add-btn"
      absolute
      fab
      top
      right
      dark
      color="primary"
      @click="add()"
    >
      <v-icon> mdi-plus </v-icon>
    </v-btn>
    <data-table
      :value="selected"
      :items="tokens"
      :loading="loading"
      :headers="tableHeaders"
      single-expand
      :expanded="expanded"
      :options="options"
      item-key="identifier"
      sort-by="symbol"
      :sort-desc="false"
      :server-items-length="serverItemLength"
      :single-select="false"
      data-cy="managed-assets-table"
      show-select
      @update:options="updatePagination($event)"
      @input="updateSelected($event)"
    >
      <template #item.symbol="{ item }">
        <asset-details-base
          :changeable="!loading"
          opens-details
          :asset="getAsset(item)"
        />
      </template>
      <template #item.address="{ item }">
        <hash-link
          v-if="item.address"
          :text="item.address"
          :chain="getChain(item.evmChain)"
        />
      </template>
      <template #item.started="{ item }">
        <date-display v-if="item.started" :timestamp="item.started" />
        <span v-else>-</span>
      </template>
      <template #item.type="{ item }">
        {{ formatType(item.assetType) }}
      </template>
      <template #item.ignored="{ item }">
        <div class="d-flex justify-center">
          <v-switch
            :input-value="isAssetIgnored(item.identifier)"
            @change="toggleIgnoreAsset(item.identifier)"
          />
        </div>
      </template>
      <template #item.actions="{ item }">
        <row-actions
          v-if="item.assetType !== CUSTOM_ASSET"
          :edit-tooltip="t('asset_table.edit_tooltip')"
          :delete-tooltip="t('asset_table.delete_tooltip')"
          @edit-click="edit(item)"
          @delete-click="deleteAsset(item)"
        >
          <copy-button
            class="mx-1"
            :tooltip="t('asset_table.copy_identifier.tooltip')"
            :value="item.identifier"
          />
        </row-actions>
      </template>
      <template #expanded-item="{ item, headers }">
        <asset-underlying-tokens :cols="headers.length" :asset="item" />
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="item.underlyingTokens && item.underlyingTokens.length > 0"
          :expanded="expanded.includes(item)"
          @click="updateExpanded(expanded.includes(item) ? [] : [item])"
        />
      </template>
    </data-table>
  </card>
</template>

<style module lang="scss">
.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>
