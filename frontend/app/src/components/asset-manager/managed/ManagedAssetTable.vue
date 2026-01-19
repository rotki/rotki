<script setup lang="ts">
import type { SupportedAsset } from '@rotki/common';
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Filters, Matcher } from '@/composables/filters/assets';
import type { Collection } from '@/types/collection';
import AssetUnderlyingTokens from '@/components/asset-manager/AssetUnderlyingTokens.vue';
import ManagedAssetActions from '@/components/asset-manager/managed/ManagedAssetActions.vue';
import ManagedAssetIgnoreSwitch from '@/components/asset-manager/managed/ManagedAssetIgnoreSwitch.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { useAssetDisplayHelpers } from '@/composables/asset-manager/use-asset-display-helpers';
import { useManagedAssetOperations } from '@/composables/asset-manager/use-managed-asset-operations';
import { useManagedAssetTable } from '@/composables/asset-manager/use-managed-asset-table';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { EVM_TOKEN, type IgnoredAssetsHandlingType, SOLANA_CHAIN, SOLANA_TOKEN } from '@/types/asset';

interface IgnoredFilter {
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}
const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const sortModel = defineModel<DataTableSortData<SupportedAsset>>('sort', { required: true });

const selected = defineModel<string[]>('selected', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

const ignoredFilter = defineModel<IgnoredFilter>('ignoredFilter', { required: true });

const expanded = defineModel<SupportedAsset[]>('expanded', { required: true });

const props = withDefaults(defineProps<{
  collection: Collection<SupportedAsset>;
  matchers: Matcher[];
  ignoredAssets: string[];
  loading?: boolean;
}>(), { loading: false });

const emit = defineEmits<{
  'refresh': [];
  'edit': [asset: SupportedAsset];
  'delete-asset': [asset: SupportedAsset];
}>();

const { collection } = toRefs(props);
const { t } = useI18n({ useScope: 'global' });

const edit = (asset: SupportedAsset) => emit('edit', asset);
const deleteAsset = (asset: SupportedAsset) => emit('delete-asset', asset);

// Use composables
const {
  loadingIgnore,
  loadingSpam,
  loadingWhitelist,
  massIgnore,
  toggleIgnoreAsset,
  toggleSpam,
  toggleWhitelistAsset,
  useIsAssetWhitelisted,
} = useManagedAssetOperations(() => emit('refresh'), ignoredFilter, selected);

const { cols, data, expand, isExpanded } = useManagedAssetTable(
  sortModel,
  paginationModel,
  expanded,
  collection,
);

const { canBeEdited, canBeIgnored, disabledRows, formatType, getAsset } = useAssetDisplayHelpers(
  collection,
  useIsAssetWhitelisted,
);

const { fetchIgnoredAssets } = useIgnoredAssetsStore();

function getAssetLocation(row: SupportedAsset): string | undefined {
  if (row.assetType === EVM_TOKEN)
    return row?.evmChain ?? undefined;

  if (row.assetType === SOLANA_TOKEN)
    return SOLANA_CHAIN;

  return undefined;
}
</script>

<template>
  <div data-cy="managed-assets-table">
    <ManagedAssetActions
      v-model:ignored-filter="ignoredFilter"
      v-model:selected="selected"
      v-model:matches="filtersModel"
      :ignored-assets="ignoredAssets"
      :matchers="matchers"
      @ignore="massIgnore($event)"
      @refresh:ignored="fetchIgnoredAssets()"
    />

    <RuiDataTable
      v-model="selected"
      v-model:pagination.external="paginationModel"
      v-model:sort.external="sortModel"
      dense
      :value="selected"
      :rows="data"
      :loading="loading"
      :cols="cols"
      :expanded="expanded"
      :disabled-rows="disabledRows"
      row-attr="identifier"
      data-cy="managed-assets-table"
      single-expand
      sticky-header
      outlined
    >
      <template #item.symbol="{ row }">
        <AssetDetailsBase
          :changeable="!loading"
          :asset="getAsset(row)"
        />
      </template>
      <template #item.address="{ row }">
        <HashLink
          v-if="row.address"
          :text="row.address"
          :location="getAssetLocation(row)"
          type="token"
        />
      </template>
      <template #item.started="{ row }">
        <DateDisplay
          v-if="row.started"
          :timestamp="row.started"
        />
        <span v-else>-</span>
      </template>
      <template #item.type="{ row }">
        {{ formatType(row.assetType) }}
      </template>
      <template #item.ignored="{ row }">
        <ManagedAssetIgnoreSwitch
          v-if="canBeIgnored(row)"
          :asset="row"
          :loading="loadingIgnore === row.identifier"
          :menu-loading="loadingWhitelist === row.identifier || loadingSpam === row.identifier"
          @toggle-ignore="toggleIgnoreAsset(row)"
          @toggle-whitelist="toggleWhitelistAsset(row.identifier)"
          @toggle-spam="toggleSpam(row)"
        />
      </template>
      <template #item.actions="{ row }">
        <RowActions
          v-if="canBeEdited(row)"
          :edit-tooltip="t('asset_table.edit_tooltip')"
          :delete-tooltip="t('asset_table.delete_tooltip')"
          @edit-click="edit(row)"
          @delete-click="deleteAsset(row)"
        >
          <CopyButton
            :tooltip="t('asset_table.copy_identifier.tooltip')"
            :value="row.identifier"
          />
        </RowActions>
      </template>
      <template #expanded-item="{ row }">
        <AssetUnderlyingTokens
          v-if="row.underlyingTokens"
          :tokens="row.underlyingTokens"
        />
      </template>
      <template #item.expand="{ row }">
        <RuiTableRowExpander
          v-if="row.underlyingTokens && row.underlyingTokens.length > 0"
          :expanded="isExpanded(row.identifier)"
          @click="expand(row)"
        />
      </template>
    </RuiDataTable>
  </div>
</template>
