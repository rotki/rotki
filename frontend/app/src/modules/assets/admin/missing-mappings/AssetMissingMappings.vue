<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-filter';
import type { CexMapping } from '@/modules/assets/types';
import type { MissingMapping } from '@/modules/user-data/schemas';
import ManageCexMappingFormDialog from '@/modules/assets/admin/cex-mapping/ManageCexMappingFormDialog.vue';
import { type MissingMappingsRequestPayload, useMissingMappingsDB } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-db';
import { useMissingMappingsFields } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-fields';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useServerTable } from '@/modules/core/table/use-server-table';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const mapping = ref<CexMapping>();

const { t } = useI18n({ useScope: 'global' });
const pillLabels = usePillBarLabels();

const cols = computed<DataTableColumn<MissingMapping>[]>(() => [{
  align: 'center',
  cellClass: 'py-3',
  key: 'location',
  label: t('common.location'),
  sortable: true,
}, {
  cellClass: 'py-3',
  key: 'identifier',
  label: t('common.asset'),
  sortable: true,
}, {
  cellClass: 'py-3 border-x border-default',
  class: 'border-x border-default',
  key: 'details',
  label: t('common.details'),
}, {
  align: 'center',
  cellClass: 'py-3 w-24',
  key: 'actions',
  label: t('common.actions_text'),
}]);

const { getData, remove } = useMissingMappingsDB();

const fields = useMissingMappingsFields();

const {
  collection: mappings,
  filter,
  pagination,
  refetch,
  sort,
} = useServerTable<MissingMapping, MissingMappingsRequestPayload, Filters>({
  fetch: getData,
  fields,
  sort: {
    default: {
      column: 'location',
      direction: 'asc',
    },
  },
});

useRememberTableSorting<MissingMapping>(TableId.ASSET_MISSING_MAPPINGS, sort, cols);

function onAddClick(item: MissingMapping) {
  set(mapping, {
    asset: '',
    location: item.location,
    locationSymbol: item.identifier,
  });
}

async function onAddComplete(item: CexMapping) {
  await remove({
    identifier: item.locationSymbol,
    location: item.location ?? '',
  });
  await refetch();
}

onMounted(async () => {
  await refetch();
});
</script>

<template>
  <TablePageLayout
    child
    hide-header
    class="lg:!-mt-5"
  >
    <RuiCard>
      <div class="mb-4 flex">
        <PillFilterBar
          v-model:matches="filter"
          class="flex-1 min-w-[12rem] md:min-w-[24rem]"
          :fields="fields"
          :labels="pillLabels"
        />
      </div>

      <RuiDataTable
        v-model:pagination.external="pagination"
        v-model:sort.external="sort"
        outlined
        dense
        stripped
        :cols="cols"
        row-attr="id"
        :rows="mappings.data"
      >
        <template #item.location="{ row }">
          <div class="flex flex-col items-center">
            <LocationDisplay :identifier="row.location" />
            <div class="text-rui-text-secondary whitespace-nowrap mt-2 font-medium">
              {{ row.name }}
            </div>
          </div>
        </template>

        <template #item.actions="{ row }">
          <div class="flex justify-center gap-2">
            <RuiButton
              variant="text"
              data-testid="row-add"
              icon
              @click="onAddClick(row)"
            >
              <RuiIcon
                size="16"
                name="lu-square-plus"
              />
            </RuiButton>
          </div>
        </template>
      </RuiDataTable>
    </RuiCard>

    <ManageCexMappingFormDialog
      v-model="mapping"
      @refresh="onAddComplete($event)"
    />
  </TablePageLayout>
</template>
