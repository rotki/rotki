<script setup lang="ts">
import type { CounterpartyMapping } from '@/modules/asset-manager/counterparty-mapping/schema';
import type { Collection } from '@/types/collection';
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import RowActions from '@/components/helper/RowActions.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import CounterpartyDisplay from '@/components/history/CounterpartyDisplay.vue';
import CounterpartyMappingFilter from '@/modules/asset-manager/counterparty-mapping/CounterpartyMappingFilter.vue';

interface ManageCounterpartyMappingTableProps {
  collection: Collection<CounterpartyMapping>;
  loading: boolean;
}

const counterpartyModel = defineModel<string | undefined>('counterparty', { required: true });

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const symbol = defineModel<string>('symbol', { required: true });

defineProps<ManageCounterpartyMappingTableProps>();

const emit = defineEmits<{
  edit: [mapping: CounterpartyMapping];
  delete: [mapping: CounterpartyMapping];
}>();

const { t } = useI18n({ useScope: 'global' });
const cols = computed<DataTableColumn<CounterpartyMapping>[]>(() => [{
  align: 'center',
  cellClass: 'py-3',
  key: 'counterparty',
  label: t('common.counterparty'),
}, {
  align: 'center',
  cellClass: 'py-3',
  key: 'counterpartySymbol',
  label: t('asset_management.cex_mapping.asset_symbol'),
}, {
  cellClass: 'py-0 border-x border-default',
  class: 'border-x border-default',
  key: 'asset',
  label: t('asset_management.cex_mapping.recognized_as'),
}, {
  key: 'actions',
  label: t('common.actions_text'),
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
        {{ t('asset_management.counterparty_mapping.subtitle') }}
      </HintMenuIcon>
      <CounterpartyMappingFilter
        v-model:counterparty="counterpartyModel"
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
          row-attr="counterparty"
          outlined
        >
          <template #item.counterparty="{ row }">
            <CounterpartyDisplay
              class="justify-center"
              :counterparty="row.counterparty"
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
