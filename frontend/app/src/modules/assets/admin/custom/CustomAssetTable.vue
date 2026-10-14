<script setup lang="ts">
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/admin/custom/use-custom-assets-filter';
import type { CustomAsset } from '@/modules/assets/types';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useCustomAssetTable } from '@/modules/assets/admin/custom/use-custom-asset-table';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import CopyButton from '@/modules/shell/components/CopyButton.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const sortModel = defineModel<DataTableSortData<CustomAsset>>('sort', { required: true });

const expandedModel = defineModel<CustomAsset[]>('expanded', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

const { assets, fields, loading = false } = defineProps<{
  assets: CustomAsset[];
  fields: FieldDef[];
  loading?: boolean;
}>();

const emit = defineEmits<{
  'edit': [asset: CustomAsset];
  'delete-asset': [asset: CustomAsset];
}>();

const { t } = useI18n({ useScope: 'global' });

const emptyState = useTableEmptyState();

const pillLabels = usePillBarLabels();

const { cols, expand, getAsset, isExpanded } = useCustomAssetTable(expandedModel);

useRememberTableSorting<CustomAsset>(TableId.CUSTOM_ASSET, sortModel, cols);

const edit = (asset: CustomAsset): void => emit('edit', asset);
const deleteAsset = (asset: CustomAsset): void => emit('delete-asset', asset);
</script>

<template>
  <TableFrame>
    <template #toolbar>
      <HintMenuIcon>
        {{ t('asset_table.custom.subtitle') }}
      </HintMenuIcon>
      <PillFilterBar
        v-model:matches="filtersModel"
        class="flex-1 min-w-48 md:min-w-96"
        :fields="fields"
        :labels="pillLabels"
      />
    </template>
    <RuiDataTable
      v-model:pagination.external="paginationModel"
      v-model:sort.external="sortModel"
      :rows="assets"
      :empty="emptyState"
      :loading="loading"
      :cols="cols"
      :expanded="expanded"
      row-attr="identifier"
      data-testid="custom-assets-table"
      single-expand
      sticky-header
      dense
      class="custom-assets-table"
    >
      <template #item.name="{ row }">
        <AssetDetailsBase :asset="getAsset(row)" />
      </template>
      <template #item.custom_asset_type="{ row }">
        <RuiChip
          size="sm"
          variant="tonal"
          color="primary"
        >
          {{ row.customAssetType }}
        </RuiChip>
      </template>
      <template #item.actions="{ row }">
        <RowActions
          align="end"
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
        <div
          class="pl-12 flex flex-col gap-0.5 max-w-prose"
          data-testid="custom-asset-notes"
        >
          <span class="text-caption font-medium text-rui-text-secondary">
            {{ t('common.notes') }}
          </span>
          <p class="m-0 text-body-2 text-rui-text whitespace-pre-line">
            {{ row.notes }}
          </p>
        </div>
      </template>
      <template #item.expand="{ row }">
        <RuiTableRowExpander
          v-if="row.notes"
          :expanded="isExpanded(row.identifier)"
          @click="expand(row)"
        />
      </template>
    </RuiDataTable>
  </TableFrame>
</template>
