<script setup lang="ts">
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/admin/custom/use-custom-assets-filter';
import type { CustomAsset } from '@/modules/assets/types';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useCustomAssetTable } from '@/modules/assets/admin/custom/use-custom-asset-table';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
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
  <RuiCard>
    <template #custom-header>
      <div class="flex items-center gap-3 px-4 pt-4">
        <HintMenuIcon>
          {{ t('asset_table.custom.subtitle') }}
        </HintMenuIcon>
        <PillFilterBar
          v-model:matches="filtersModel"
          class="flex-1 min-w-[12rem] md:min-w-[24rem]"
          :fields="fields"
          :labels="pillLabels"
        />
      </div>
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
      outlined
      dense
      class="custom-assets-table"
    >
      <template #item.name="{ row }">
        <AssetDetailsBase :asset="getAsset(row)" />
      </template>
      <template #item.custom_asset_type="{ row }">
        <BadgeDisplay>
          {{ row.customAssetType }}
        </BadgeDisplay>
      </template>
      <template #item.actions="{ row }">
        <RowActions
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
        <RuiCard>
          <div class="font-bold">
            {{ t('common.notes') }}:
          </div>
          <div class="pt-2">
            {{ row.notes }}
          </div>
        </RuiCard>
      </template>
      <template #item.expand="{ row }">
        <RuiTableRowExpander
          v-if="row.notes"
          :expanded="isExpanded(row.identifier)"
          @click="expand(row)"
        />
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
