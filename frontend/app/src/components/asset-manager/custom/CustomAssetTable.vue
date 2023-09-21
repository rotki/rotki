<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import { type TablePagination } from '@/types/pagination';
import {
  type CustomAsset,
  type CustomAssetRequestPayload
} from '@/types/asset';
import {
  type Filters,
  type Matcher
} from '@/composables/filters/custom-assets';

withDefaults(
  defineProps<{
    assets: CustomAsset[];
    expanded: CustomAsset[];
    options: TablePagination<CustomAsset>;
    serverItemLength: number;
    matchers: Matcher[];
    filters: Filters;
    loading?: boolean;
  }>(),
  { loading: false }
);

const emit = defineEmits<{
  (e: 'add'): void;
  (e: 'edit', asset: CustomAsset): void;
  (e: 'delete-asset', asset: CustomAsset): void;
  (e: 'update:pagination', pagination: CustomAssetRequestPayload): void;
  (e: 'update:filters', filters: Filters): void;
  (e: 'update:expanded', expandedAssets: CustomAsset[]): void;
}>();

const { t } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.asset'),
    value: 'name',
    width: '50%'
  },
  {
    text: t('common.type'),
    value: 'custom_asset_type',
    width: '50%'
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
const edit = (asset: CustomAsset) => emit('edit', asset);
const deleteAsset = (asset: CustomAsset) => emit('delete-asset', asset);
const updatePagination = (pagination: CustomAssetRequestPayload) =>
  emit('update:pagination', pagination);
const updateFilter = (filters: Filters) => emit('update:filters', filters);
const updateExpanded = (expandedAssets: CustomAsset[]) =>
  emit('update:expanded', expandedAssets);

const getAsset = (item: CustomAsset) => ({
  name: item.name,
  symbol: item.customAssetType,
  identifier: item.identifier,
  isCustomAsset: true,
  customAssetType: item.customAssetType
});
</script>

<template>
  <Card>
    <template #title>
      {{ t('common.assets') }}
    </template>
    <template #subtitle>
      {{ t('asset_table.custom.subtitle') }}
    </template>
    <template #actions>
      <VRow>
        <VCol class="d-none d-md-block" />
        <VCol cols="12" md="6" class="pb-md-8">
          <TableFilter
            :matches="filters"
            :matchers="matchers"
            @update:matches="updateFilter($event)"
          />
        </VCol>
      </VRow>
    </template>
    <VBtn
      absolute
      fab
      top
      right
      dark
      color="primary"
      data-cy="add-manual-asset"
      @click="add()"
    >
      <VIcon> mdi-plus </VIcon>
    </VBtn>
    <DataTable
      :items="assets"
      :loading="loading"
      :headers="tableHeaders"
      single-expand
      :expanded="expanded"
      :options="options"
      item-key="identifier"
      sort-by="name"
      class="custom-assets-table"
      :sort-desc="false"
      :server-items-length="serverItemLength"
      @update:options="updatePagination($event)"
    >
      <template #item.name="{ item }">
        <AssetDetailsBase
          :changeable="!loading"
          opens-details
          :asset="getAsset(item)"
        />
      </template>
      <template #item.custom_asset_type="{ item }">
        <BadgeDisplay>
          {{ item.customAssetType }}
        </BadgeDisplay>
      </template>
      <template #item.actions="{ item }">
        <RowActions
          :edit-tooltip="t('asset_table.edit_tooltip')"
          :delete-tooltip="t('asset_table.delete_tooltip')"
          @edit-click="edit(item)"
          @delete-click="deleteAsset(item)"
        >
          <CopyButton
            class="mx-1"
            :tooltip="t('asset_table.copy_identifier.tooltip')"
            :value="item.identifier"
          />
        </RowActions>
      </template>
      <template #expanded-item="{ item }">
        <TableExpandContainer visible :colspan="tableHeaders.length">
          <div class="font-bold">{{ t('asset_table.notes') }}:</div>
          <div class="pt-2">
            {{ item.notes }}
          </div>
        </TableExpandContainer>
      </template>
      <template #item.expand="{ item }">
        <RowExpander
          v-if="item.notes"
          :expanded="expanded.includes(item)"
          @click="updateExpanded(expanded.includes(item) ? [] : [item])"
        />
      </template>
    </DataTable>
  </Card>
</template>
