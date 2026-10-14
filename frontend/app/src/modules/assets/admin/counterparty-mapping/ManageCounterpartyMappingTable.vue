<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { CounterpartyMapping } from '@/modules/assets/admin/counterparty-mapping/schema';
import type { Filters } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-filter';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

interface ManageCounterpartyMappingTableProps {
  collection: Collection<CounterpartyMapping>;
  fields: FieldDef[];
  loading: boolean;
}

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

defineProps<ManageCounterpartyMappingTableProps>();

const emit = defineEmits<{
  edit: [mapping: CounterpartyMapping];
  delete: [mapping: CounterpartyMapping];
}>();

const { t } = useI18n({ useScope: 'global' });
const pillLabels = usePillBarLabels();
const emptyState = useTableEmptyState();
const cols = computed<DataTableColumn<CounterpartyMapping>[]>(() => [{
  cellClass: 'py-2',
  key: 'counterparty',
  label: t('common.counterparty'),
}, {
  cellClass: 'py-2 font-medium',
  key: 'counterpartySymbol',
  label: t('asset_management.cex_mapping.asset_symbol'),
}, {
  cellClass: 'py-0',
  key: 'asset',
  label: t('asset_management.cex_mapping.recognized_as'),
}, {
  align: 'end',
  cellClass: 'w-px',
  key: 'actions',
  label: t('common.actions_text'),
}]);
</script>

<template>
  <TableFrame>
    <template #toolbar>
      <HintMenuIcon>
        {{ t('asset_management.counterparty_mapping.subtitle') }}
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
      :rows="collection.data"
      dense
      :loading="loading"
      :cols="cols"
      :empty="emptyState"
      row-attr="counterparty"
    >
      <template #item.counterparty="{ row }">
        <CounterpartyDisplay :counterparty="row.counterparty" />
      </template>
      <template #item.asset="{ row }">
        <AssetDetails :asset="row.asset" />
      </template>
      <template #item.actions="{ row }">
        <RowActions
          align="end"
          :edit-tooltip="t('asset_table.edit_tooltip')"
          :delete-tooltip="t('asset_table.delete_tooltip')"
          @edit-click="emit('edit', row)"
          @delete-click="emit('delete', row)"
        />
      </template>
    </RuiDataTable>
  </TableFrame>
</template>
