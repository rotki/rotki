<script setup lang="ts">
import type { TablePaginationData } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/admin/counterparty-mapping/counterparty-mapping-filter-keys';
import type { CounterpartyMapping } from '@/modules/assets/admin/counterparty-mapping/schema';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import MappingAdminTable from '@/modules/assets/admin/MappingAdminTable.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

defineProps<{
  collection: Collection<CounterpartyMapping>;
  fields: FieldDef[];
  loading: boolean;
  /** What a row's delete button asks; `delete` is emitted once the user confirms. */
  deleteConfirm: (mapping: CounterpartyMapping) => { title: string; message: string };
}>();

const emit = defineEmits<{
  edit: [mapping: CounterpartyMapping];
  delete: [mapping: CounterpartyMapping];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <MappingAdminTable
    v-model:pagination="paginationModel"
    v-model:filters="filtersModel"
    :collection="collection"
    :fields="fields"
    :loading="loading"
    :delete-confirm="deleteConfirm"
    :subtitle="t('asset_management.counterparty_mapping.subtitle')"
    source-key="counterparty"
    :source-label="t('common.counterparty')"
    symbol-key="counterpartySymbol"
    @edit="emit('edit', $event)"
    @delete="emit('delete', $event)"
  >
    <template #source="{ row }">
      <CounterpartyDisplay :counterparty="row.counterparty" />
    </template>
  </MappingAdminTable>
</template>
