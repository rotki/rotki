<script setup lang="ts">
import RowActions from '@/components/helper/RowActions.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import ExchangeInput from '@/components/inputs/ExchangeInput.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/types/collection';
import type { CexMapping } from '@/types/asset';

const locationModel = defineModel<string | undefined>('location', { required: true });

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

withDefaults(
  defineProps<{
    collection: Collection<CexMapping>;
    symbol?: string;
    loading: boolean;
  }>(),
  {
    symbol: undefined,
  },
);

const emit = defineEmits<{
  (e: 'update:symbol', symbol?: string): void;
  (e: 'edit', mapping: CexMapping): void;
  (e: 'delete', mapping: CexMapping): void;
}>();

const { t } = useI18n();
const tableHeaders = computed<DataTableColumn<CexMapping>[]>(() => [
  {
    align: 'center',
    cellClass: 'py-3',
    key: 'location',
    label: t('asset_management.cex_mapping.exchange'),
  },
  {
    align: 'center',
    cellClass: 'py-3',
    key: 'locationSymbol',
    label: t('asset_management.cex_mapping.location_symbol'),
  },
  {
    cellClass: 'py-0 border-x border-default',
    class: 'border-x border-default',
    key: 'asset',
    label: t('asset_management.cex_mapping.recognized_as'),
  },
  {
    key: 'actions',
    label: '',
  },
]);

const edit = (mapping: CexMapping) => emit('edit', mapping);
const deleteMapping = (mapping: CexMapping) => emit('delete', mapping);
const onSymbolChange = useDebounceFn((value?: string) => emit('update:symbol', value), 500);

function setPage(page: number) {
  set(paginationModel, {
    ...get(paginationModel),
    page,
  });
}
</script>

<template>
  <div>
    <div class="flex sm:items-center justify-between mb-4">
      <HintMenuIcon>
        {{ t('asset_management.cex_mapping.subtitle') }}
      </HintMenuIcon>
      <div class="w-full md:w-[40rem] flex flex-col sm:flex-row gap-4">
        <ExchangeInput
          v-model="locationModel"
          :label="t('asset_management.cex_mapping.filter_by_exchange')"
          class="w-full"
          dense
          hide-details
          clearable
        />
        <RuiTextField
          :model-value="symbol"
          class="w-full sm:max-w-72"
          variant="outlined"
          color="primary"
          :label="t('asset_management.cex_mapping.filter_by_location_symbol')"
          clearable
          hide-details
          dense
          @update:model-value="onSymbolChange($event)"
        />
      </div>
    </div>
    <CollectionHandler
      :collection="collection"
      @set-page="setPage($event)"
    >
      <template #default="{ data }">
        <RuiDataTable
          v-model:pagination.external="paginationModel"
          :rows="data"
          dense
          striped
          :loading="loading"
          :cols="tableHeaders"
          :sticky-offset="64"
          row-attr="location"
          outlined
        >
          <template #item.location="{ row }">
            <div
              v-if="!row.location"
              class="flex flex-col gap-1 items-center"
            >
              <div class="icon-bg">
                <RuiIcon
                  name="lu-building-2"
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
