<script setup lang="ts">
import AssetManagerMoreTitle from '@/modules/assets/admin/AssetManagerMoreTitle.vue';
import ManageCexMappingFormDialog from '@/modules/assets/admin/cex-mapping/ManageCexMappingFormDialog.vue';
import { useAssetMissingMappings } from '@/modules/assets/admin/missing-mappings/use-asset-missing-mappings';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });
const pillLabels = usePillBarLabels();

/** The exchange's name for the asset of the row being mapped, the dialog's clue to what it is. */
const addingName = ref<string>();

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
  <TablePageLayout child>
    <template #title>
      <AssetManagerMoreTitle />
    </template>
    <TableFrame>
      <template #toolbar>
        <PillFilterBar
          v-model:matches="modelFilter"
          class="flex-1 min-w-48 md:min-w-96"
          :fields="fields"
          :labels="pillLabels"
        />
      </template>

      <RuiDataTable
        v-model:pagination.external="pagination"
        v-model:sort.external="sort"
        dense
        :cols="cols"
        :empty="emptyState"
        row-attr="id"
        :rows="mappings.data"
      >
        <template #item.location="{ row }">
          <LocationDisplay
            horizontal
            :identifier="row.location"
          />
        </template>

        <template #item.identifier="{ row }">
          <div class="flex flex-col">
            <span class="font-medium text-rui-text">{{ row.identifier }}</span>
            <span
              v-if="row.name"
              class="text-sm text-rui-text-secondary"
            >
              {{ row.name }}
            </span>
          </div>
        </template>

        <template #item.actions="{ row }">
          <div class="flex justify-end">
            <RuiButton
              size="sm"
              variant="text"
              color="primary"
              class="whitespace-nowrap"
              data-testid="row-add"
              @click="addingName = row.name || undefined; onAddClick(row)"
            >
              <template #prepend>
                <RuiIcon
                  size="16"
                  name="lu-plus"
                />
              </template>
              {{ t('asset_management.cex_mapping.add_mapping') }}
            </RuiButton>
          </div>
        </template>
      </RuiDataTable>
    </TableFrame>

    <ManageCexMappingFormDialog
      v-model="modelMapping"
      :exchange-name="addingName"
      @refresh="onAddComplete($event)"
    />
  </TablePageLayout>
</template>
