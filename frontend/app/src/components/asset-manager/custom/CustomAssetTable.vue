<script setup lang="ts">
import { some } from 'lodash-es';
import type {
  DataTableColumn,
  DataTableOptions,
  DataTableSortData,
} from '@rotki/ui-library-compat';
import type { TablePagination } from '@/types/pagination';
import type { CustomAsset } from '@/types/asset';
import type {
  Filters,
  Matcher,
} from '@/composables/filters/custom-assets';

const props = withDefaults(
  defineProps<{
    assets: CustomAsset[];
    expanded: CustomAsset[];
    options: TablePagination<CustomAsset>;
    serverItemLength: number;
    matchers: Matcher[];
    filters: Filters;
    loading?: boolean;
  }>(),
  { loading: false },
);

const emit = defineEmits<{
  (e: 'edit', asset: CustomAsset): void;
  (e: 'delete-asset', asset: CustomAsset): void;
  (e: 'update:options', pagination: DataTableOptions): void;
  (e: 'update:filters', filters: Filters): void;
  (e: 'update:expanded', expandedAssets: CustomAsset[]): void;
}>();

const { t } = useI18n();

const sort: Ref<DataTableSortData> = ref({
  column: 'name',
  direction: 'desc' as const,
});

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: t('common.asset'),
    key: 'name',
    class: 'w-1/2',
    cellClass: 'py-0',
    sortable: true,
  },
  {
    label: t('common.type'),
    key: 'custom_asset_type',
    class: 'w-1/2',
    cellClass: 'py-0',
    sortable: true,
  },
  {
    label: '',
    key: 'actions',
    cellClass: 'py-0',
  },
]);

const edit = (asset: CustomAsset) => emit('edit', asset);
const deleteAsset = (asset: CustomAsset) => emit('delete-asset', asset);

function updatePagination(options: DataTableOptions) {
  emit('update:options', options);
}

const updateFilter = (filters: Filters) => emit('update:filters', filters);

function updateExpanded(expandedAssets: CustomAsset[]) {
  return emit('update:expanded', expandedAssets);
}

function getAsset(item: CustomAsset) {
  return {
    name: item.name,
    symbol: item.customAssetType,
    identifier: item.identifier,
    isCustomAsset: true,
    customAssetType: item.customAssetType,
  };
}

function isExpanded(identifier: string) {
  return some(props.expanded, { identifier });
}

function expand(item: CustomAsset) {
  updateExpanded(isExpanded(item.identifier) ? [] : [item]);
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
            :matches="filters"
            :matchers="matchers"
            @update:matches="updateFilter($event)"
          />
        </div>
      </div>
    </template>
    <RuiDataTable
      :rows="assets"
      :loading="loading"
      :cols="tableHeaders"
      :expanded="expanded"
      :pagination="{
        limit: options.itemsPerPage,
        page: options.page,
        total: serverItemLength,
      }"
      :pagination-modifiers="{ external: true }"
      :sort.sync="sort"
      :sort-modifiers="{ external: true }"
      row-attr="identifier"
      data-cy="custom-assets-table"
      single-expand
      sticky-header
      outlined
      class="custom-assets-table"
      @update:options="updatePagination($event)"
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
