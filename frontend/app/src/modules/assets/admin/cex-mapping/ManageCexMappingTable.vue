<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/admin/cex-mapping/use-cex-mapping-filter';
import type { CexMapping } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
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
const cols = computed<DataTableColumn<CexMapping>[]>(() => [{
  align: 'center',
  cellClass: 'py-3',
  key: 'location',
  label: t('common.exchange'),
}, {
  align: 'center',
  cellClass: 'py-3',
  key: 'locationSymbol',
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
        {{ t('asset_management.cex_mapping.subtitle') }}
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
