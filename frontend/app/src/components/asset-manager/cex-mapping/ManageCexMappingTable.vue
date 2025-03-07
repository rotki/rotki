<script setup lang="ts">
import type { CexMapping } from '@/types/asset';
import type { Collection } from '@/types/collection';
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import ExchangeMappingFilter from '@/components/asset-manager/cex-mapping/ExchangeMappingFilter.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import RowActions from '@/components/helper/RowActions.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';

interface ManageCexMappingTableProps {
  collection: Collection<CexMapping>;
  loading: boolean;
}

const locationModel = defineModel<string | undefined>('location', { required: true });

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const symbol = defineModel<string>('symbol', { required: true });

defineProps<ManageCexMappingTableProps>();

const emit = defineEmits<{
  edit: [mapping: CexMapping];
  delete: [mapping: CexMapping];
}>();

const { t } = useI18n();
const cols = computed<DataTableColumn<CexMapping>[]>(() => [{
  align: 'center',
  cellClass: 'py-3',
  key: 'location',
  label: t('asset_management.cex_mapping.exchange'),
}, {
  align: 'center',
  cellClass: 'py-3',
  key: 'locationSymbol',
  label: t('asset_management.cex_mapping.location_symbol'),
}, {
  cellClass: 'py-0 border-x border-default',
  class: 'border-x border-default',
  key: 'asset',
  label: t('asset_management.cex_mapping.recognized_as'),
}, {
  key: 'actions',
  label: '',
}]);

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
      <ExchangeMappingFilter
        v-model:location="locationModel"
        v-model:symbol="symbol"
      />
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
          :cols="cols"
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
              @edit-click="emit('edit', row)"
              @delete-click="emit('delete', row)"
            />
          </template>
        </RuiDataTable>
      </template>
    </CollectionHandler>
  </div>
</template>
