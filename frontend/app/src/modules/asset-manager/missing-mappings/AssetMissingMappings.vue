<script setup lang="ts">
import z from 'zod';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useMissingMappingsDB } from '@/modules/asset-manager/missing-mappings/use-missing-mappings-db';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import ManageCexMappingFormDialog from '@/components/asset-manager/cex-mapping/ManageCexMappingFormDialog.vue';
import ExchangeMappingFilter from '@/components/asset-manager/cex-mapping/ExchangeMappingFilter.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import type { CexMapping } from '@/types/asset';
import type { DataTableColumn } from '@rotki/ui-library';
import type { MissingMapping } from '@/modules/data/schemas';

const QuerySchema = z.object({
  identifier: z.string().optional().default(''),
  location: z.string().optional(),
});

const mapping = ref<CexMapping>();
const location = ref<string>();
const symbol = ref<string>('');

const { t } = useI18n({ useScope: 'global' });

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
  key: 'details',
  label: t('common.details'),
}, {
  align: 'center',
  cellClass: 'py-3 w-24',
  key: 'actions',
  label: '',
}]);

const { getData, remove } = useMissingMappingsDB();

const {
  fetchData,
  filters,
  matchers,
  pagination,
  sort,
  state: mappings,
} = usePaginationFilters<MissingMapping>(getData, {
  defaultSortBy: {
    column: 'location',
    direction: 'asc',
  },
  extraParams: computed(() => ({
    identifier: get(symbol),
    location: get(location),
  })),
  onUpdateFilters(query) {
    const params = QuerySchema.parse(query);
    if (params.identifier) {
      set(symbol, params.identifier);
    }
    if (params.location) {
      set(location, params.location);
    }
  },
});

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
  await fetchData();
}

onMounted(async () => {
  await fetchData();
});
</script>

<template>
  <TablePageLayout
    child
    class="md:-mt-[4.5rem]"
  >
    <RuiCard>
      <div class="mb-4 flex justify-end">
        <ExchangeMappingFilter
          v-model:location="location"
          v-model:symbol="symbol"
        />
      </div>

      <RuiDataTable
        v-model:filters="filters"
        v-model:matchers="matchers"
        v-model:pagination.external="pagination"
        v-model:sort.external="sort"
        outlined
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
              data-cy="row-add"
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
