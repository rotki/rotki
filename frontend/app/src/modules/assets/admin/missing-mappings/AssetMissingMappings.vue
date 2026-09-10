<script setup lang="ts">
import ManageCexMappingFormDialog from '@/modules/assets/admin/cex-mapping/ManageCexMappingFormDialog.vue';
import { useAssetMissingMappings } from '@/modules/assets/admin/missing-mappings/use-asset-missing-mappings';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const pillLabels = usePillBarLabels();

const {
  cols,
  error,
  fields,
  mappings,
  modelFilter,
  modelMapping,
  onAddClick,
  onAddComplete,
  pagination,
  refetch,
  sort,
} = useAssetMissingMappings();

const emptyState = useTableEmptyState({ error });

useRememberTableSorting(TableId.ASSET_MISSING_MAPPINGS, sort, cols);

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
          v-model:matches="modelFilter"
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
        :empty="emptyState"
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
      v-model="modelMapping"
      @refresh="onAddComplete($event)"
    />
  </TablePageLayout>
</template>
