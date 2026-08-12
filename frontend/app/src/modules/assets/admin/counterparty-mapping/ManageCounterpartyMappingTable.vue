<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { CounterpartyMapping } from '@/modules/assets/admin/counterparty-mapping/schema';
import type { Filters } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-filter';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
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
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-4">
      <HintMenuIcon>
        {{ t('asset_management.counterparty_mapping.subtitle') }}
      </HintMenuIcon>
      <PillFilterBar
        v-model:matches="filtersModel"
        class="flex-1 min-w-[12rem] md:min-w-[24rem]"
        :fields="fields"
        :labels="pillLabels"
      />
    </div>
    <RuiDataTable
      v-model:pagination.external="paginationModel"
      :rows="collection.data"
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
        <AssetDetails :asset="row.asset" />
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
  </div>
</template>
