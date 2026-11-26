<script setup lang="ts">
import type { Filters } from '@/modules/assets/prices/oracle-price-filter-keys';
import type { OraclePriceEntry, OraclePricesQuery } from '@/modules/assets/prices/price-types';
import { set } from '@vueuse/shared';
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import OraclePriceEditDialog from '@/modules/assets/prices/components/oracle/OraclePriceEditDialog.vue';
import OraclePriceTable from '@/modules/assets/prices/components/oracle/OraclePriceTable.vue';
import { useOraclePriceFields } from '@/modules/assets/prices/use-oracle-price-fields';
import { useOraclePrices } from '@/modules/assets/prices/use-oracle-prices';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';

defineSlots<{
  /** the page's tab switch, at the start of the toolbar */
  tabs?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const { deletePrice, fetchData } = useOraclePrices();

const fields = useOraclePriceFields();
const pillLabels = usePillBarLabels();

const {
  collection,
  error,
  filter,
  isLoading: loading,
  pagination,
  refetch: refresh,
} = useServerTable<
  OraclePriceEntry,
  OraclePricesQuery,
  Filters
>({
  fetch: fetchData,
  fields,
  sort: {
    default: {
      column: 'timestamp',
      direction: 'desc',
    },
  },
});

const emptyState = useTableEmptyState({ error });

const editingItem = ref<OraclePriceEntry>();

function startEdit(item: OraclePriceEntry): void {
  set(editingItem, { ...item });
}

async function deleteRow(item: OraclePriceEntry): Promise<void> {
  if (await deletePrice(item))
    await refresh();
}

onMounted(async () => {
  await refresh();
});

// for the page header's refresh button
defineExpose({
  loading,
  refresh,
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <TableFrame>
      <template #toolbar>
        <slot name="tabs" />
        <HintMenuIcon>
          {{ t('oracle_prices.hint') }}
        </HintMenuIcon>
        <PillFilterBar
          v-model:matches="filter"
          class="flex-1 min-w-48 md:min-w-96"
          :fields="fields"
          :labels="pillLabels"
        />
      </template>

      <OraclePriceTable
        v-model:pagination="pagination"
        :rows="collection.data"
        :loading="loading"
        :disabled="loading"
        :empty-state="emptyState"
        @delete="deleteRow($event)"
        @edit="startEdit($event)"
      />
    </TableFrame>

    <OraclePriceEditDialog
      v-model="editingItem"
      @refresh="refresh()"
    />
  </div>
</template>
