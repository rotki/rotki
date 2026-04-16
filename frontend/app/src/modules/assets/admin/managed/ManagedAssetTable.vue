<script setup lang="ts">
import type { SupportedAsset } from '@rotki/common';
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { Filters, Matcher } from '@/modules/core/table/filters/use-assets-filter';
import AssetUnderlyingTokens from '@/modules/assets/admin/AssetUnderlyingTokens.vue';
import ManagedAssetActions from '@/modules/assets/admin/managed/ManagedAssetActions.vue';
import ManagedAssetIgnoreSwitch from '@/modules/assets/admin/managed/ManagedAssetIgnoreSwitch.vue';
import { useAssetDisplayHelpers } from '@/modules/assets/admin/use-asset-display-helpers';
import { useManagedAssetOperations } from '@/modules/assets/admin/use-managed-asset-operations';
import { useManagedAssetTable } from '@/modules/assets/admin/use-managed-asset-table';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import { EVM_TOKEN, type IgnoredAssetsHandlingType, isSpammableAssetType, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import CopyButton from '@/modules/shell/components/CopyButton.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

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

const { collection, ignoredAssets, loading = false, matchers } = defineProps<{
  collection: Collection<SupportedAsset>;
  matchers: Matcher[];
  ignoredAssets: string[];
  loading?: boolean;
}>();

const emit = defineEmits<{
  'refresh': [];
  'edit': [asset: SupportedAsset];
  'delete-asset': [asset: SupportedAsset];
}>();
const { t } = useI18n({ useScope: 'global' });

const edit = (asset: SupportedAsset) => emit('edit', asset);
const deleteAsset = (asset: SupportedAsset) => emit('delete-asset', asset);

// Use composables
const {
  isAssetWhitelisted,
  loadingIgnore,
  loadingSpam,
  loadingWhitelist,
  massIgnore,
  massSpam,
  toggleIgnoreAsset,
  toggleSpam,
  toggleWhitelistAsset,
} = useManagedAssetOperations(() => emit('refresh'), ignoredFilter, selected);

const { cols, data, expand, isExpanded } = useManagedAssetTable(
  sortModel,
  paginationModel,
  expanded,
  () => collection,
);

const { canBeEdited, canBeIgnored, disabledRows, formatType, getAsset } = useAssetDisplayHelpers(
  () => collection,
  isAssetWhitelisted,
);

const { fetchIgnoredAssets } = useIgnoredAssetOperations();

const spamDisabled = computed<boolean>(() => {
  const selectedIds = get(selected);
  if (selectedIds.length === 0)
    return false;

  const assets = collection.data;
  return !selectedIds.some((id) => {
    const asset = assets.find(a => a.identifier === id);
    return asset && isSpammableAssetType(asset.assetType);
  });
});

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
      :spam-disabled="spamDisabled"
      @ignore="massIgnore($event)"
      @mark-spam="massSpam()"
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
