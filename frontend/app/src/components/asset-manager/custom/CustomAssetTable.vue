<script setup lang="ts">
import type { Filters, Matcher } from '@/composables/filters/custom-assets';
import type { CustomAsset } from '@/types/asset';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { some } from 'es-toolkit/compat';

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const sortModel = defineModel<DataTableSortData<CustomAsset>>('sort', { required: true });

const expandedModel = defineModel<CustomAsset[]>('expanded', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

withDefaults(
  defineProps<{
    assets: CustomAsset[];
    matchers: Matcher[];
    loading?: boolean;
  }>(),
  { loading: false },
);

const emit = defineEmits<{
  (e: 'edit', asset: CustomAsset): void;
  (e: 'delete-asset', asset: CustomAsset): void;
}>();

const { t } = useI18n();

const cols = computed<DataTableColumn<CustomAsset>[]>(() => [
  {
    cellClass: 'py-0',
    class: 'w-1/2',
    key: 'name',
    label: t('common.asset'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
    class: 'w-1/2',
    key: 'custom_asset_type',
    label: t('common.type'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
    key: 'actions',
    label: '',
  },
]);

useRememberTableSorting<CustomAsset>(TableId.CUSTOM_ASSET, sortModel, cols);

const edit = (asset: CustomAsset) => emit('edit', asset);
const deleteAsset = (asset: CustomAsset) => emit('delete-asset', asset);

function getAsset(item: CustomAsset) {
  return {
    customAssetType: item.customAssetType,
    identifier: item.identifier,
    isCustomAsset: true,
    name: item.name,
    symbol: item.customAssetType,
  };
}

function isExpanded(identifier: string) {
  return some(get(expandedModel), { identifier });
}

function expand(item: CustomAsset) {
  set(expandedModel, isExpanded(item.identifier) ? [] : [item]);
}
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex justify-between px-4 pt-4">
        <HintMenuIcon>
          {{ t('asset_table.custom.subtitle') }}
        </HintMenuIcon>
        <div class="w-full sm:max-w-[25rem] self-center">
          <TableFilter
            v-model:matches="filtersModel"
            :matchers="matchers"
          />
        </div>
      </div>
    </template>
    <RuiDataTable
      v-model:pagination.external="paginationModel"
      v-model:sort.external="sortModel"
      :rows="assets"
      :loading="loading"
      :cols="cols"
      :expanded="expanded"
      row-attr="identifier"
      data-cy="custom-assets-table"
      single-expand
      sticky-header
      outlined
      dense
      class="custom-assets-table"
    >
      <template #item.name="{ row }">
        <AssetDetailsBase
          :changeable="!loading"
          opens-details
          :asset="getAsset(row)"
        />
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
