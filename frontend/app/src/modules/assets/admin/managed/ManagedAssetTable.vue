<script setup lang="ts">
import type { SupportedAsset } from '@rotki/common';
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/admin/managed/use-assets-filter';
import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import type { PillParams } from '@/modules/core/table/param-refs';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import AssetUnderlyingTokens from '@/modules/assets/admin/AssetUnderlyingTokens.vue';
import ManagedAssetActions from '@/modules/assets/admin/managed/ManagedAssetActions.vue';
import ManagedAssetIgnoreSwitch from '@/modules/assets/admin/managed/ManagedAssetIgnoreSwitch.vue';
import { useAssetDisplayHelpers } from '@/modules/assets/admin/use-asset-display-helpers';
import { useManagedAssetOperations } from '@/modules/assets/admin/use-managed-asset-operations';
import { useManagedAssetTable } from '@/modules/assets/admin/use-managed-asset-table';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import CopyButton from '@/modules/shell/components/CopyButton.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

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
const { t } = useI18n({ useScope: 'global' });

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
  <div data-testid="managed-assets-table">
    <ManagedAssetActions
      v-model:pill-params="pillParams"
      v-model:selected="selected"
      v-model:matches="filtersModel"
      :ignored-handling="ignoredHandling"
      :fields="fields"
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
      :empty="emptyState"
      :loading="loading"
      :cols="cols"
      :expanded="expanded"
      :disabled-rows="disabledRows"
      row-attr="identifier"
      data-testid="managed-assets-table"
      single-expand
      sticky-header
      outlined
    >
      <template #item.symbol="{ row }">
        <div class="flex items-center gap-2">
          <AssetDetailsBase :asset="getAsset(row)" />
          <RuiChip
            v-if="row.isRebasing"
            color="primary"
            size="sm"
            variant="outlined"
            class="shrink-0"
          >
            {{ t('common.rebasing_token') }}
          </RuiChip>
        </div>
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
