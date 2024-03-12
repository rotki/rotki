<script setup lang="ts">
import type { CexMapping } from '@/types/asset';
import type { Collection } from '@/types/collection';
import type { DataTableColumn, DataTableOptions } from '@rotki/ui-library-compat';
import type { TablePagination } from '@/types/pagination';

const props = defineProps<{
  collection: Collection<CexMapping>;
  location: string;
  loading: boolean;
  options: TablePagination<CexMapping>;
}>();

const emit = defineEmits<{
  (e: 'update:location', location: string): void;
  (e: 'update:page', page: number): void;
  (e: 'update:options', options: DataTableOptions): void;
  (e: 'edit', mapping: CexMapping): void;
  (e: 'delete', mapping: CexMapping): void;
}>();

const { t } = useI18n();
const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: t('asset_management.cex_mapping.exchange'),
    key: 'location',
    align: 'center',
    cellClass: 'py-3',
  },
  {
    label: t('asset_management.cex_mapping.location_symbol'),
    key: 'locationSymbol',
    align: 'center',
    cellClass: 'py-3',
  },
  {
    label: t('asset_management.cex_mapping.recognized_as'),
    key: 'asset',
    class: 'border-x border-default',
    cellClass: 'py-0 border-x border-default',
  },
  {
    label: '',
    key: 'actions',
  },
]);

const locationModel = useVModel(props, 'location', emit);

function setPage(page: number) {
  emit('update:page', page);
}

function updatePagination(options: DataTableOptions) {
  emit('update:options', options);
}

const edit = (mapping: CexMapping) => emit('edit', mapping);
const deleteMapping = (mapping: CexMapping) => emit('delete', mapping);
</script>

<template>
  <div>
    <div class="flex justify-between">
      <HintMenuIcon>
        {{ t('asset_management.cex_mapping.subtitle') }}
      </HintMenuIcon>
      <div class="w-full md:w-[25rem]">
        <ExchangeInput
          v-model="locationModel"
          :label="t('asset_management.cex_mapping.filter_by_exchange')"
          dense
          clearable
        />
      </div>
    </div>
    <CollectionHandler
      :collection="collection"
      @set-page="setPage($event)"
    >
      <template #default="{ data, found }">
        <RuiDataTable
          :rows="data"
          dense
          striped
          :loading="loading"
          :cols="tableHeaders"
          :pagination="{
            limit: options.itemsPerPage,
            page: options.page,
            total: found,
          }"
          :pagination-modifiers="{ external: true }"
          :sticky-offset="64"
          row-attr=""
          outlined
          @update:options="updatePagination($event)"
        >
          <template #item.location="{ row }">
            <div
              v-if="!row.location"
              class="flex flex-col gap-1 items-center"
            >
              <div class="icon-bg">
                <RuiIcon
                  name="exchange-dollar-line"
                  color="secondary"
                />
              </div>
              <div class="text-rui-text-secondary whitespace-nowrap">
                {{ t('asset_management.cex_mapping.all_exchanges') }}
              </div>
            </div>
            <LocationDisplay
              v-else
              :identifier="row.location"
            />
          </template>
          <template #item.asset="{ row }">
            <AssetDetails
              opens-details
              hide-name
              :asset="row.asset"
            />
          </template>
          <template #item.actions="{ row }">
            <RowActions
              :edit-tooltip="t('asset_table.edit_tooltip')"
              :delete-tooltip="t('asset_table.delete_tooltip')"
              @edit-click="edit(row)"
              @delete-click="deleteMapping(row)"
            />
          </template>
        </RuiDataTable>
      </template>
    </CollectionHandler>
  </div>
</template>
