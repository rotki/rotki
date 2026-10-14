<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/admin/cex-mapping/use-cex-mapping-filter';
import type { CexMapping } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

interface ManageCexMappingTableProps {
  collection: Collection<CexMapping>;
  fields: FieldDef[];
  loading: boolean;
}

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

defineProps<ManageCexMappingTableProps>();

const emit = defineEmits<{
  edit: [mapping: CexMapping];
  delete: [mapping: CexMapping];
}>();

const { t } = useI18n({ useScope: 'global' });
const pillLabels = usePillBarLabels();
const emptyState = useTableEmptyState();
const cols = computed<DataTableColumn<CexMapping>[]>(() => [{
  cellClass: 'py-2',
  key: 'location',
  label: t('common.exchange'),
}, {
  cellClass: 'py-2 font-medium',
  key: 'locationSymbol',
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
        {{ t('asset_management.cex_mapping.subtitle') }}
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
      row-attr="location"
    >
      <template #item.location="{ row }">
        <div
          v-if="!row.location"
          class="flex items-center gap-2 text-rui-text-secondary whitespace-nowrap"
        >
          <RuiIcon
            name="lu-building-2"
            size="20"
          />
          {{ t('asset_management.cex_mapping.all_exchanges') }}
        </div>
        <LocationDisplay
          v-else
          :identifier="row.location"
        />
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
