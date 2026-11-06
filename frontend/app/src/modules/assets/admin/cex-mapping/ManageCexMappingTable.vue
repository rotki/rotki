<script setup lang="ts">
import type { TablePaginationData } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/admin/cex-mapping/cex-mapping-filter-keys';
import type { CexMapping } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import MappingAdminTable from '@/modules/assets/admin/MappingAdminTable.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

defineProps<{
  collection: Collection<CexMapping>;
  fields: FieldDef[];
  loading: boolean;
  /** What a row's delete button asks; `delete` is emitted once the user confirms. */
  deleteConfirm: (mapping: CexMapping) => { title: string; message: string };
}>();

const emit = defineEmits<{
  edit: [mapping: CexMapping];
  delete: [mapping: CexMapping];
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
    :subtitle="t('asset_management.cex_mapping.subtitle')"
    source-key="location"
    :source-label="t('common.exchange')"
    symbol-key="locationSymbol"
    @edit="emit('edit', $event)"
    @delete="emit('delete', $event)"
  >
    <template #source="{ row }">
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
  </MappingAdminTable>
</template>
