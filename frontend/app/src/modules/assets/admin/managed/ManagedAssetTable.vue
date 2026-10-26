<script setup lang="ts">
import type { SupportedAsset } from '@rotki/common';
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/admin/managed/asset-filter-keys';
import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import type { PillParams } from '@/modules/core/table/param-refs';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import AssetUnderlyingTokens from '@/modules/assets/admin/AssetUnderlyingTokens.vue';
import ManagedAssetActions from '@/modules/assets/admin/managed/ManagedAssetActions.vue';
import ManagedAssetIgnoreSwitch from '@/modules/assets/admin/managed/ManagedAssetIgnoreSwitch.vue';
import ManagedAssetName from '@/modules/assets/admin/managed/ManagedAssetName.vue';
import ManagedAssetRowActions from '@/modules/assets/admin/managed/ManagedAssetRowActions.vue';
import { useAssetDisplayHelpers } from '@/modules/assets/admin/use-asset-display-helpers';
import { useManagedAssetOperations } from '@/modules/assets/admin/use-managed-asset-operations';
import { useManagedAssetTable } from '@/modules/assets/admin/use-managed-asset-table';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const sortModel = defineModel<DataTableSortData<SupportedAsset>>('sort', { required: true });

const selected = defineModel<string[]>('selected', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

const pillParams = defineModel<PillParams>('pillParams', { required: true });

const expanded = defineModel<SupportedAsset[]>('expanded', { required: true });

const { collection, ignoredHandling, loading = false } = defineProps<{
  collection: Collection<SupportedAsset>;
  fields: FieldDef[];
  /** Read-only here: it decides whether an ignore action needs the table re-fetched. */
  ignoredHandling: IgnoredAssetsHandlingType;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'refresh': [];
  'edit': [asset: SupportedAsset];
  'delete-asset': [asset: SupportedAsset];
}>();

const selectionMode = shallowRef<boolean>(false);

/** `undefined` outside selection mode, which is what makes the table drop its checkbox column. */
const tableSelection = computed<string[] | undefined>({
  get: () => (get(selectionMode) ? get(selected) : undefined),
  set: (value?: string[]) => set(selected, value ?? []),
});

const edit = (asset: SupportedAsset) => emit('edit', asset);
const deleteAsset = (asset: SupportedAsset) => emit('delete-asset', asset);

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
} = useManagedAssetOperations(() => emit('refresh'), () => ignoredHandling, selected);

const { cols, data, emptyState, expand, getAssetLocation, isExpanded, spamDisabled } = useManagedAssetTable(
  paginationModel,
  expanded,
  () => collection,
  selected,
);

useRememberTableSorting<SupportedAsset>(TableId.SUPPORTED_ASSET, sortModel, cols);

const { canBeEdited, canBeIgnored, disabledRows, formatType, getAsset } = useAssetDisplayHelpers(
  () => collection,
  isAssetWhitelisted,
);

const { fetchIgnoredAssets } = useIgnoredAssetOperations();
</script>

<template>
  <TableFrame data-testid="managed-assets-table">
    <template #toolbar>
      <ManagedAssetActions
        v-model:pill-params="pillParams"
        v-model:selected="selected"
        v-model:selection-mode="selectionMode"
        v-model:matches="filtersModel"
        :ignored-handling="ignoredHandling"
        :fields="fields"
        :spam-disabled="spamDisabled"
        @ignore="massIgnore($event)"
        @mark-spam="massSpam()"
        @refresh:ignored="fetchIgnoredAssets()"
      />
    </template>

    <RuiDataTable
      v-model="tableSelection"
      v-model:pagination.external="paginationModel"
      v-model:sort.external="sortModel"
      dense
      :rows="data"
      :empty="emptyState"
      :loading="loading"
      :cols="cols"
      :expanded="expanded"
      :disabled-rows="disabledRows"
      row-attr="identifier"
      data-testid="managed-assets-table"
      single-expand
      sticky-header
    >
      <template #item.symbol="{ row }">
        <ManagedAssetName
          :asset="getAsset(row)"
          :rebasing="!!row.isRebasing"
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
        <ManagedAssetRowActions
          v-if="canBeEdited(row)"
          :identifier="row.identifier"
          @edit="edit(row)"
          @delete="deleteAsset(row)"
        />
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
  </TableFrame>
</template>
